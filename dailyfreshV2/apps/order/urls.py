from django.urls import path
from .views import *

app_name='order'

urlpatterns=[
    path('place',OrderPlaceView.as_view(),name='place'), #购物车提交订单显示页面
    path('place1',OrderPlace1View.as_view(),name='place1'), #商品直接购买显示订单页面
    path('commit',OrderCommitView.as_view(),name='commit'),
    path('pay',OrderPayView.as_view(),name='pay'),
    path('check',CheckPayView.as_view(),name='check'),
    path('comment/<int:order_id>',CommentView.as_view(),name='comment'),
]