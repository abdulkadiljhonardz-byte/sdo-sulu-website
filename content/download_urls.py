from django.urls import path
from .views import download_resource
app_name="downloads"
urlpatterns=[path("<int:pk>/",download_resource,name="file")]
