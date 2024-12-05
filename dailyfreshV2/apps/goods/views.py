from django.shortcuts import render
from django.views import View
from user.models import *
from django.http import HttpResponse,JsonResponse
from django.core.paginator import Paginator
from django_redis import get_redis_connection

# Create your views here.


class IndexView(View):
    def get(self, request):
        """首页"""
        # 获取商品种类信息
        types = GoodsType.objects.all()
        # 获取首页轮播商品信息
        goods_banners = IndexGoodsBanner.objects.all().order_by("index")
        # 获取首页促销活动信息
        promotion_banners = IndexPromotionBanner.objects.all().order_by("index")

        # 获取首页分类商品展示信息
        for type in types:
            # 获取种类图片
            image_banners = IndexTypeGoodsBanner.objects.filter(
                type=type, display_type=1
            ).order_by("index")
            # 获取种类名称
            title_banners = IndexTypeGoodsBanner.objects.filter(
                type=type, display_type=0
            ).order_by("index")

            # 动态增加属性
            type.image_banners = image_banners
            type.title_banners = title_banners

        context = {
            "types": types,
            "goods_banners": goods_banners,
            "promotion_banners": promotion_banners,
        }
        
        user=request.user
        cart_count=0
        if user.is_authenticated:
            conn=get_redis_connection('default')
            cart_key='cart_%d'%user.id
            cart_count=conn.hlen(cart_key)
        
        context.update(cart_count=cart_count)


        return render(request, "index.html", context)


class DetailView(View):
    """详情页"""

    def get(self, request, id):
        # 查询该商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=id)
        except GoodsSKU.DoesNotExist:
            return HttpResponse("该商品不存在")

        # 获取商品分类信息
        types = GoodsType.objects.all()
        # 获取商品品论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment="")
        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by("-create_time")[:2]

        # 获取同种商品的不同规格
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=id)
        # 获取对应商品评论
        order_goods=OrderGoods.objects.filter(sku_id=id)
        
        # 加入购物车功能
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection("default")
            cart_key = "cart_%d" % user.id
            cart_count = conn.hlen(cart_key)

            # 用户历史记录
            history_key = "history_%d" % user.id
            conn.lrem(history_key, 0, id)
            conn.lpush(history_key, id)
            # 只保存用户最近浏览的5条信息
            conn.ltrim(history_key, 0, 4)

        context = {
            "sku": sku,
            "types": types,
            "sku_orders": sku_orders,
            "new_skus": new_skus,
            "same_spu_skus": same_spu_skus,
            "cart_count": cart_count,
            'order_goods':order_goods,
        }
        return render(request, "detail.html", context)
    # def post(self,request,id):
    #     '''直接购买商品'''
    #     user=request.user
    #     if not user.is_authenticated:
    #         return JsonResponse({"res": 0, "errmsg": "用户未登录"})
    #     sku_id=request.POST.get('sku_id')
    #     count=request.POST.get('count')
    #     count=int(count)
    #     if not all([sku_id,count]):
    #         return JsonResponse({"res": 1, "errmsg": "数据不完整"})
    #     # 检查商品是否存在
    #     try:
    #         sku = GoodsSKU.objects.get(id=sku_id)
    #     except GoodsSKU.DoesNotExist:
    #         return JsonResponse({"res": 3, "errmsg": "商品不存在"}) 
    #     conn=get_redis_connection('default')
    #     cart_key='cart_%d'%user.id
        
    #     # 检查商品库存
    #     if count > sku.stock:
    #         return JsonResponse({"res": 4, "errmsg": "商品库存不足"})
    #     # 保存sku_id count到redis
    #     conn.hset(cart_key,sku_id,count)
    #     return JsonResponse({'res':5,'msg':'正在生成订单'})


class ListView(View):
    """列表页"""

    def get(self, request, type_id, page):
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return HttpResponse("种类不存在")
        types = GoodsType.objects.all()
        sort = request.GET.get("sort")
        if sort == "price":
            skus = GoodsSKU.objects.filter(type=type).order_by("price")  # 升序降序?
        elif sort == "hot":
            skus = GoodsSKU.objects.filter(type=type).order_by("-sales")
        else:
            sort == "default"
            skus = GoodsSKU.objects.filter(type=type).order_by("-id")

        paginator = Paginator(skus, 1)

        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1

        skus_page = paginator.page(page)

        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by("-create_time")[:2]

        context = {
            "type": type,
            "types": types,
            "skus_page": skus_page,
            "new_skus": new_skus,
            "pages": pages,
            "sort": sort,
        }

        return render(request, "list.html", context)
