from django.urls import path
from .views import check
app_name="verification"
urlpatterns=[path("",check,name="check")]
