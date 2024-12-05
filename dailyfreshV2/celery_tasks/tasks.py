from django.core.mail import send_mail
from django.conf import settings
from django.template import loader
from celery import Celery
import time
import os

# celery启动命令 
# celery -A djangoProject1 worker --concurrency=4 --loglevel=INFO -P threads
# celery -A celery_tasks.main worker --pool=solo -l info


# 启动celery需要这几句
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfreshV2.settings')
django.setup()

from user.models import *

# 创建celery实例对象
app=Celery('celery_tasks.tasks',broker='redis://127.0.0.1:6379/1')

@app.task
def send_register_active_email(to_email,username,token):
    '''发送激活邮件'''
    subject='天天生鲜欢迎信息'
    message=''
    sender=settings.DEFAULT_FROM_EMAIL
    receiver=[to_email]
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (username, token, token)

    send_mail(subject=subject,message=message,from_email=sender,recipient_list=receiver,html_message=html_message)

    time.sleep(5)

@app.task
def generate_static_index_html():
    '''产生首页静态页面'''
    types=GoodsType.objects.all()
    goods_banners=IndexGoodsBanner.objects.all().order_by('index')
    promotion_banners=IndexPromotionBanner.objects.all().order_by('index')

    for type in types:
        image_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by('index')
        title_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=0).order_by('index')

        # 动态给type增加属性
        type.image_banners=image_banners
        type.title_banners=title_banners

    # 组织模板上下文
    context={
        'types':types,
        'goods_banners':goods_banners,
        'promotion_banners':promotion_banners
    }
    # 加载模板对象，返回模板对象
    temp = loader.get_template('static_index.html')
    # 渲染模板
    static_index_html=temp.render(context)

    # 生成静态模板
    save_path=os.path.join(settings.BASE_DIR,'static/index.html')
    with open(save_path,'w') as f:
        f.write(static_index_html)

