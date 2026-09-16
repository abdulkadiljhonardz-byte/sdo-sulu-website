from django.urls import path
from .views import detail, download, index
app_name="issuances"
urlpatterns=[path("",index,name="list"),path("<int:pk>/",detail,name="detail"),path("<int:pk>/download/",download,name="download")]
