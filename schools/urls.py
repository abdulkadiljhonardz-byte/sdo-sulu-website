from django.urls import path
from . import views
app_name="schools"; urlpatterns=[path("",views.directory,name="directory"),path("<int:pk>/",views.detail,name="detail")]
