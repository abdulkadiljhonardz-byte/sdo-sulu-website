from django.urls import path
from . import views
app_name="content"; urlpatterns=[path("",views.news_list,name="news"),path("<slug:slug>/",views.news_detail,name="news_detail")]
