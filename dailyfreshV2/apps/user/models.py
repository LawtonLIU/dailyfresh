from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel
from tinymce.models import HTMLField
# Create your models here.

class User(AbstractUser,BaseModel):
    '''用户模型类'''
    class Meta:
        db_table = 'df_user'
        verbose_name='用户'
        verbose_name_plural=verbose_name

class AddressManager(models.Manager):
    '''地址模型管理器类'''
    # 改变原有查询的结果集all（）
    def get_default_address(self,user):
        '''获取用户默认收货地址'''
        try:
            address = self.get(user=user,is_default=True)
        except self.model.DoesNotExist:
            # 不存在默认收货地址
            address=None
        
        return address

class Address(BaseModel):
    '''地址类模型'''
    user=models.ForeignKey('User',verbose_name='所属账户',on_delete=models.CASCADE)
    receiver=models.CharField(max_length=20,verbose_name='收件人')
    addr=models.CharField(max_length=256,verbose_name='收件地址')
    zip_code=models.CharField(max_length=6,null=True,verbose_name='邮政编码')
    phone=models.CharField(max_length=11,verbose_name='联系电话')
    is_default=models.BooleanField(default=False,verbose_name='是否默认')

    # 自定义模型管理对象
    objects = AddressManager()

    class Meta:
        db_table='df_address'
        verbose_name='地址'
        verbose_name_plural=verbose_name

class OrderInfo(BaseModel):
    '''订单模型类'''
    PAY_METHODS = {
        '1': "货到付款",
        '2': "微信支付",
        '3': "支付宝",
        '4': '银联支付'
    }

    PAY_METHODS_ENUM = {
        "CASH": 1,
        "ALIPAY": 2
    }

    ORDER_STATUS_ENUM = {
        "UNPAID": 1,
        "UNSEND": 2,
        "UNRECEIVED": 3,
        "UNCOMMENT": 4,
        "FINISHED": 5
    }

    PAY_METHOD_CHOICES = (
        (1, '货到付款'),
        (2, '微信支付'),
        (3, '支付宝'),
        (4, '银联支付')
    )

    ORDER_STATUS = {
        1:'待支付',
        2:'待发货',
        3:'待收货',
        4:'待评价',
        5:'已完成'
    }

    ORDER_STATUS_CHOICES = (
        (1, '待支付'),
        (2, '待发货'),
        (3, '待收货'),
        (4, '待评价'),
        (5, '已完成')
    )

    order_id=models.CharField(max_length=128,primary_key=True,verbose_name='订单id')
    user=models.ForeignKey('User',verbose_name='用户',on_delete=models.CASCADE)
    addr=models.ForeignKey('Address',verbose_name='地址',on_delete=models.CASCADE)
    pay_method=models.SmallIntegerField(choices=PAY_METHOD_CHOICES,default=3,verbose_name='支付方式')
    total_count=models.IntegerField(default=1,verbose_name='商品数量')
    total_price=models.DecimalField(max_digits=10,decimal_places=2,verbose_name='商品总价')
    transit_price=models.DecimalField(max_digits=10,decimal_places=2,verbose_name='订单运费')
    order_status=models.SmallIntegerField(choices=ORDER_STATUS_CHOICES,default=1,verbose_name='订单状态')
    trade_no=models.CharField(max_length=128,default='',verbose_name='支付编号')

    class Meta:
        db_table='df_order_info'
        verbose_name='订单'
        verbose_name_plural=verbose_name
        
class OrderGoods(BaseModel):
    '''订单商品模型类'''
    order=models.ForeignKey('OrderInfo',verbose_name='订单',on_delete=models.CASCADE)
    sku=models.ForeignKey('GoodsSKU',verbose_name='商品sku',on_delete=models.CASCADE)
    count=models.IntegerField(default=1,verbose_name='商品数目')
    price=models.DecimalField(max_digits=10,decimal_places=2,verbose_name='商品价格')
    comment=models.CharField(max_length=256,default='',verbose_name='评论')
    
    class Meta:
        db_table='df_order_goods'
        verbose_name='订单商品'
        verbose_name_plural=verbose_name

class GoodsType(BaseModel):
    '''商品类型模型类'''
    name=models.CharField(max_length=20,verbose_name='种类名称')
    logo=models.CharField(max_length=20,verbose_name='标识')
    image=models.ImageField(upload_to='type',verbose_name='商品类型图片')

    def __str__(self):
        return self.name

    class Meta:
        db_table='df_goods_type'
        verbose_name='商品种类'
        verbose_name_plural=verbose_name

class GoodsSKU(BaseModel):
    '''商品SKU模型类'''
    status_choices=(
        (0,'下线'),
        (1,'上线'),
    )
    
    type=models.ForeignKey('GoodsType',verbose_name='商品种类',on_delete=models.CASCADE)
    goods=models.ForeignKey('Goods',verbose_name='商品SPU',on_delete=models.CASCADE)
    name = models.CharField(max_length=20, verbose_name='商品名称')
    desc = models.CharField(max_length=256, verbose_name='商品简介')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
    unite = models.CharField(max_length=20, verbose_name='商品单位')
    image = models.ImageField(upload_to='goods', verbose_name='商品图片')
    stock = models.IntegerField(default=1, verbose_name='商品库存')
    sales = models.IntegerField(default=0, verbose_name='商品销量')
    status = models.SmallIntegerField(default=1, choices=status_choices, verbose_name='商品状态')

    def __str__(self):
        return self.name
    
    class Meta:
        db_table='df_goods_sku'
        verbose_name='商品SKU'
        verbose_name_plural=verbose_name

class Goods(BaseModel):
    '''商品SPU模型''' 
    name=models.CharField(max_length=20,verbose_name='商品SPU名称')
    # 富文本类型：带有格式的文本
    detail=HTMLField(blank=True,verbose_name='商品详情')
    
    def __str__(self):
        return self.name

    class Meta:
        db_table='df_goods'
        verbose_name='商品SPU'
        verbose_name_plural=verbose_name

class GoodsImage(BaseModel):
    '''商品图片模型类'''
    sku=models.ForeignKey('GoodsSKU',verbose_name='商品',on_delete=models.CASCADE)
    image=models.ImageField(upload_to='goods',verbose_name='图片路径')

    class Meta:
        db_table='df_goods_image'
        verbose_name='商品图片'
        verbose_name_plural=verbose_name

class IndexGoodsBanner(BaseModel):
    '''首页轮播商品展示模型类'''
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品',on_delete=models.CASCADE)
    image = models.ImageField(upload_to='banner', verbose_name='图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序') # 0 1 2 3

    def __str__(self):
        return self.sku.name

    class Meta:
        db_table = 'df_index_banner'
        verbose_name = '首页轮播商品'
        verbose_name_plural = verbose_name


class IndexTypeGoodsBanner(BaseModel):
    '''首页分类商品展示模型类'''
    DISPLAY_TYPE_CHOICES = (
        (0, "标题"),
        (1, "图片")
    )

    type = models.ForeignKey('GoodsType', verbose_name='商品类型',on_delete=models.CASCADE)
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品SKU',on_delete=models.CASCADE)
    display_type = models.SmallIntegerField(default=1, choices=DISPLAY_TYPE_CHOICES, verbose_name='展示类型')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    def __str__(self):
        return self.type.name

    class Meta:
        db_table = 'df_index_type_goods'
        verbose_name = "主页分类展示商品"
        verbose_name_plural = verbose_name


class IndexPromotionBanner(BaseModel):
    '''首页促销活动模型类'''
    name = models.CharField(max_length=20, verbose_name='活动名称')
    url = models.CharField(max_length=256, verbose_name='活动链接')
    image = models.ImageField(upload_to='banner', verbose_name='活动图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'df_index_promotion'
        verbose_name = "主页促销活动"
        verbose_name_plural = verbose_name    
    





    