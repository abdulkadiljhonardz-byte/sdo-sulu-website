from django.urls import path
from .views import index
app_name="events"
urlpatterns=[path("",index,name="list")]
