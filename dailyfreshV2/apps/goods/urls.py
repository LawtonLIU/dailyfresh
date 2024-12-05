from django.urls import path
from .views import *
app_name='goods'

urlpatterns=[
    path('index',IndexView.as_view(),name='index'),
    path('goods/<int:id>',DetailView.as_view(),name='detail'),
    path('goods/list/<int:type_id>/<int:page>',ListView.as_view(),name='list'),
]