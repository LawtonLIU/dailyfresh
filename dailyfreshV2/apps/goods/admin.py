from django.contrib import admin
from user.models import *
# Register your models here.

class GoodsTypeAdmin(admin.ModelAdmin):    
    pass

class IndexGoodsBannerAdmin(admin.ModelAdmin):
    pass


class IndexTypeGoodsBannerAdmin(admin.ModelAdmin):
    pass


class IndexPromotionBannerAdmin(admin.ModelAdmin):
    pass

class GoodsAdmin(admin.ModelAdmin):
    pass

class GoodsSKUAdmin(admin.ModelAdmin):
    pass

admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(Goods,GoodsAdmin)
admin.site.register(GoodsSKU,GoodsSKUAdmin)