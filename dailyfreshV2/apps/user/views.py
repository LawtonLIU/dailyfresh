from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from .models import *
import re
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from celery_tasks.tasks import send_register_active_email
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django_redis import get_redis_connection
from django.core.paginator import Paginator
# Create your views here.

class RegisterView(View):
    '''注册 CBV'''
    def get(self,request):
        return render(request,'register.html')

    def post(self,request):
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 进行业务处理: 进行用户注册
        user = User.objects.create_user(username, email, password)
        user.is_active = False
        user.save()

        # 发送激活邮件 有效时间10分钟
        serializer=Serializer(settings.SECRET_KEY,600) 
        info={'user_id':user.id}
        token=serializer.dumps(info) #bytes
        token=token.decode() #加密

        # 发邮件 使用celery实现异步操作
        send_register_active_email.delay(email,username,token)

        return redirect(reverse('user:login'))

class ActiveView(View):
    '''用户激活'''
    def get(self,request,token):
        serializer=Serializer(settings.SECRET_KEY,600)
        try:
            info=serializer.loads(token)
            user_id=info['user_id']
            user=User.objects.get(id=user_id)
            user.is_active=True
            user.save()
            # return redirect(reverse('user:login'))
            return HttpResponse('用户激活成功')
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse('激活链接已过期')
        
# user/login/
class LoginView(View):
    '''登录'''
    def get(self,request):
        return render(request,'login.html')
    
    def post(self,request):
        #  接收数据 用户名 密码 
        username=request.POST.get('username')
        password=request.POST.get('pwd')

        if not all([username,password]):
            return HttpResponse('数据不完整')
        
        # 登录校验
        user=authenticate(username=username,password=password)
        if user is not None:
            if user.is_active:
                # 记录用户登录状态
                login(request,user)
                # 是否记住用户名
                remember=request.POST.get('remember')
                response=redirect(reverse('goods:index'))
                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username',username,max_age=3600*24*7) #一周后过期
                else:
                    response.delete_cookie('username')
                
                return response
            else:
                return HttpResponse('用户未激活')
        else:
            return HttpResponse('用户名或密码错误')
        
class LogoutView(View):
    '''退出登录'''
    def get(self,request):
        logout(request)
        return redirect(reverse('goods:index'))

class UserInfoView(LoginRequiredMixin,View):
    '''个人信息页'''
    def get(self,request):
        user=request.user
        address=Address.objects.get_default_address(user)
        conn=get_redis_connection('default')
        history_key='history_%d'%user.id
        sku_ids=conn.lrange(history_key,0,4)
        goods_li=[]
        for id in sku_ids:
            goods=GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        context={
            'page':'user',
            'address':address,
            'goods_li':goods_li,
        }
        return render(request,'user_center_info.html',context)
    
class UserOrderView(LoginRequiredMixin,View):
    '''用户中心-订单页'''
    def get(self,request,page):
        user=request.user
        orders=OrderInfo.objects.filter(user=user).order_by('-create_time')
        for order in orders:
            order_skus=OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                amount=order_sku.count*order_sku.price
                order_sku.amount=amount
            order.status_name=OrderInfo.ORDER_STATUS[order.order_status]
            order.order_skus=order_skus
        paginator=Paginator(orders,1)
        try:
            page=int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page=1
        order_page=paginator.page(page)
        num_pages=paginator.num_pages
        if num_pages < 5:
            pages=range(1,num_pages+1)
        elif page <= 3:
            pages=range(1,6)
        elif num_pages - page <= 2:
            pages=range(num_pages-4,num_pages+1)
        else:
            pages=range(page-2,page+3)
        
        context={
            'order_page':order_page,
            'pages':pages,
            'page':'order'
        }


        return render(request,'user_center_order.html',context)

class AddressView(LoginRequiredMixin,View):
    '''用户中心--地址页'''
    def get(self,request):
        user=request.user
        try:
            address=Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            address=None
        return render(request,'user_center_site.html',{'address':address,'page':'address'})

    def post(self,request):
        # 地址添加
        receiver=request.POST.get('receiver')
        addr=request.POST.get('addr')
        zip_code=request.POST.get('zip_code')
        phone=request.POST.get('phone')
        if not all([receiver,addr,zip_code,phone]):
            return render(request,'user_center_site.html',{'errmsg':'数据不完整'})
        # 校验手机号
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request,'user_center_site.html',{'errmsg':'手机格式不正确'})
        user=request.user
        address=Address.objects.get_default_address(user)
        if address:
            is_default=False
        else:
            is_default=True
        Address.objects.create(user=user,receiver=receiver,addr=addr,phone=phone,is_default=is_default)

        return redirect(reverse('user:address'))





        







