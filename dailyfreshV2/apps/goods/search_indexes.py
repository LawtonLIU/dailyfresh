from haystack import indexes
from user.models import *
class GoodsSKUIndex(indexes.SearchIndex,indexes.Indexable):
    '''商品索引类'''
    text=indexes.CharField(document=True,use_template=True)
    def get_model(self):
        return GoodsSKU
    
    def index_queryset(self, using=None):
        return self.get_model().objects.all()
