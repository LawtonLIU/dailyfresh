from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django_redis import get_redis_connection
from django.http import HttpResponse, JsonResponse
from user.models import *
from django.db import transaction
from datetime import datetime
from django.conf import settings
from alipay import AliPay
import os


# Create your views here.
class OrderPlaceView(View):
    """提交订单显示页面"""
    def post(self, request):
        # 需要得到什么？ 商品id 商品信息 价格 总价格 数量
        user = request.user
        sku_ids = request.POST.getlist("sku_ids")
        if not sku_ids:
            return redirect(reverse("cart:show"))
        conn = get_redis_connection("default")
        cart_key = "cart_%d" % user.id
        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            # 根据id获取商品信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 商品数量
            count = conn.hget(cart_key, sku_id)
            count = count.decode("utf-8")
            # 计算商品小计
            amount = sku.price * int(count)
            sku.count = count
            sku.amount = amount
            skus.append(sku)
            # 计算商品总件数和总价格
            total_price += amount
            total_count += int(count)

        # 运费 无系统 写死10元
        transit_price = 10
        # 实付款
        total_pay = total_price + transit_price
        # 用户收件地址
        addrs = Address.objects.filter(user=user)
        sku_ids = ",".join(sku_ids)  # [1,2] -> 1,2
        context = {
            "skus": skus,
            "total_count": total_count,
            "total_pay": total_pay,
            "total_price": total_price,
            "transit_price": transit_price,
            "addrs": addrs,
            "sku_ids": sku_ids,
        }
        return render(request, "place_order.html", context)


class OrderPlace1View(View):
    '''商品直接购买订单页面显示'''
    def post(self,request):    
        user=request.user
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count') 
        count=int(count)
        print(sku_id)
        print(count)
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            print('商品不存在')
        conn=get_redis_connection('default')
        cart_key='cart_%d'%user.id
        conn.hset(cart_key,sku_id,count)
        skus = []
        total_count = 0
        total_price = 0
        amount=sku.price*count
        sku.amount=amount
        sku.count=count
        skus.append(sku)
        total_count=count
        total_price=sku.price*count
        addrs = Address.objects.filter(user=user)
        # 运费 无系统 写死10元
        transit_price = 10
        total_pay=total_price+transit_price
        sku_ids=sku_id
        context = {
                "skus": skus,
                "total_count": total_count,
                "total_pay": total_pay,
                "total_price": total_price,
                "transit_price": transit_price,
                "addrs": addrs,
                "sku_ids": sku_ids,
            }
        return render(request, "place_order.html",context)

class OrderCommitView(View):
    """订单提交"""

    @transaction.atomic  # 确保块内所有数据库操作要么全部成功，要么全部失败
    def post(self, request):
        # 订单创建
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res": 0, "errmsg": "用户未登录"})
        addr_id = request.POST.get("addr_id")
        pay_method = request.POST.get("pay_method")
        sku_ids = request.POST.get("sku_ids")
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({"res": 1, "errmsg": "参数不完整"})
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({"res": 2, "errmsg": "非法的支付方式"})
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({"res": 3, "errmsg": "地址非法"})

        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)
        transit_price = 10
        total_count = 0
        total_price = 0
        # 事务保存点
        save_id = transaction.savepoint()
        try:
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=transit_price,
            )
            conn = get_redis_connection("default")
            cart_key = "cart_%d" % user.id
            sku_ids = sku_ids.split(",")
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.select_for_update().get(
                        id=sku_id
                    )  # 更新数据库信息
                except:
                    # 商品不存在
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({"res": 4, "errmsg": "商品不存在"})

                count = conn.hget(cart_key, sku_id)
                count = count.decode("utf-8")
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({"res": 6, "errmsg": "商品库存不足"})
                OrderGoods.objects.create(
                    order=order, sku=sku, count=count, price=sku.price
                )
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                amount = sku.price * int(count)
                total_price += amount
                total_count += int(count)
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({"res": 7, "errmsg": "下单失败"})

        transaction.savepoint_commit(save_id)
        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({"res": 5, "message": "创建成功"})


class OrderPayView(View):
    """订单支付"""
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res": 0, "errmsg": "用户未登录"})
        order_id = request.POST.get("order_id")
        if not order_id:
            return JsonResponse({"res": 1, "errmsg": "无效的订单id"})
        try:
            order = OrderInfo.objects.get(
                order_id=order_id, user=user, pay_method=3, order_status=1
            )
        except OrderInfo.DoesNotExist:
            return JsonResponse({"res": 2, "errmsg": "订单错误"})
        # 总金额
        total_pay = order.total_price + order.transit_price
        
        # 调用支付宝接口
        with open('apps/order/app_private_key.pem','r') as file:
            app_private_key_string=file.read()
        with open('apps/order/alipay_public_key.pem','r') as file:
            alipay_public_key_string=file.read()
        
        alipay = AliPay(
            appid="9021000140681898",
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,
            debug=True,
        )
        order_url = alipay.api_alipay_trade_page_pay(
            out_trade_no=str(order_id),
            total_amount=str(total_pay),
            subject="天天生鲜%s" % order_id,
        )
        pay_url = "https://openapi-sandbox.dl.alipaydev.com/gateway.do?" + order_url
        return JsonResponse({"res": 3, "pay_url": pay_url})


class CheckPayView(View):
    """检查支付"""
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res": 0, "errmsg": "用户未登录"})
        order_id = request.POST.get("order_id")
        if not order_id:
            return JsonResponse({"res": 1, "errmsg": "无效的订单id"})
        try:
            order = OrderInfo.objects.get(
                order_id=order_id, user=user, pay_method=3, order_status=1
            )
        except OrderInfo.DoesNotExist:
            return JsonResponse({"res": 2, "errmsg": "订单错误"})

        # 调用支付宝接口
        with open('apps/order/app_private_key.pem','r') as file:
            app_private_key_string=file.read()
        with open('apps/order/alipay_public_key.pem','r') as file:
            alipay_public_key_string=file.read()
        
        alipay = AliPay(
            appid="9021000140681898",
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,
            debug=True,
        )

        while True:
            response = alipay.api_alipay_trade_query(order_id)
            code = response.get("code")
            if code == "10000" and response.get("trade_status") == "TRADE_SUCCESS":
                trade_no = response.get("trade_no")
                order.trade_no = trade_no
                order.order_status = 4
                order.save()
                return JsonResponse({"res": 3, "message": "支付成功"})
            elif code == "40004" or (
                code == "10000" and response.get("trade_status") == "WAIT_BUYER_PAY"
            ):
                import time

                time.sleep(5)
                continue
            else:
                print(code)
                return JsonResponse({"res": 4, "errmsg": "支付失败"})


class CommentView(View):
    """评论"""
    def get(self,request,order_id):
        user=request.user
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order=OrderInfo.objects.get(order_id=order_id,user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))
        order.status_name=OrderInfo.ORDER_STATUS[order.order_status]
        order_skus=OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            amount=order_sku.count*order_sku.price
            order_sku.amount=amount
        order.order_skus=order_skus
        return render(request,'order_comment.html',{'order':order})
    def post(self,request,order_id):
        user=request.user
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))
        total_count=request.POST.get('total_count')
        total_count=int(total_count)
        for i in range(1,total_count+1):
            sku_id=request.POST.get('sku_%d'%i)
            content=request.POST.get('content_%d'%i,'')
            try:
                order_goods=OrderGoods.objects.get(order=order,sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.comment=content
            order_goods.save()
        order.order_status=5
        order.save()
        return redirect(reverse('user:order',kwargs={'page':1}))


