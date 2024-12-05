from django.shortcuts import render
from django.views import View
from django.http import JsonResponse, HttpResponse
from user.models import *
from django_redis import get_redis_connection

# Create your views here.


class CartInfoView(View):
    """购物车显示页面"""

    def get(self, request):
        # 加入到购物车的数据
        # 商品信息存在redis中的
        user = request.user
        if user.is_authenticated:
            conn = get_redis_connection("default")
            cart_key = "cart_%d" % user.id
            cart_dict = conn.hgetall(cart_key)
            skus = []
            total_count = 0
            total_price = 0
            for sku_id, count in cart_dict.items():
                # 将bytes类型转为字符类型
                sku_id=int(sku_id.decode('utf-8'))
                count=int(count.decode('utf-8'))
                # 获取商品信息
                sku = GoodsSKU.objects.get(id=sku_id)
                # 计算商品小计
                amount = sku.price * int(count)
                sku.amount = amount
                sku.count = count
                skus.append(sku)
                total_count += int(count)
                total_price += amount
            context = {
                "total_count": total_count,
                "total_price": total_price,
                "skus": skus,
            }
            return render(request, "cart.html", context)
        else:
            return HttpResponse("请先登录")


class CartAddView(View):
    """购物车添加记录"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res": 0, "errmsg": "请先登录"})

        # 接收数据
        sku_id = request.POST.get("sku_id")
        count = request.POST.get("count")
        count = int(count)

        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({"res": 1, "errmsg": "数据不完整"})

        # 检查商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({"res": 3, "errmsg": "商品不存在"})

        conn = get_redis_connection("default")
        cart_key = "cart_%d" % user.id
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)
        # 校验商品库存
        if count > sku.stock:
            return JsonResponse({"res": 4, "errmsg": "商品库存不足"})
        conn.hset(cart_key, sku_id, count)
        total_count = conn.hlen(cart_key)

        return JsonResponse(
            {"res": 5, "total_count": total_count, "message": "添加成功"}
        )


class CartUpdateView(View):
    """购物车记录更新"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res": 0, "errmsg": "请先登录"})

        sku_id = request.POST.get("sku_id")
        count = request.POST.get("count")
        count = int(count)

        if not all([sku_id, count]):
            return JsonResponse({"res": 1, "errmsg": "数据不完整"})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({"res": 3, "errmsg": "商品不存在"})

        # 业务处理:更新购物车记录
        conn = get_redis_connection("default")
        cart_key = "cart_%d" % user.id

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({"res": 4, "errmsg": "商品库存不足"})

        # 更新
        conn.hset(cart_key, sku_id, count)

        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        return JsonResponse(
            {"res": 5, "total_count": total_count, "message": "更新成功"}
        )


class CartDeleteView(View):
    """购物车记录删除"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res": 0, "errmsg": "请先登录"})

        sku_id = request.POST.get("sku_id")
        if not sku_id:
            return JsonResponse({"res": 1, "errmsg": "无效商品"})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({"res": 2, "errmsg": "商品不存在"})

        # 业务处理，在redis中删除sku_id
        conn = get_redis_connection("default")
        cart_key = "cart_%d" % user.id
        conn.hdel(cart_key, sku_id)
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse(
            {"res": 3, "total_count": total_count, "message": "删除成功"}
        )
