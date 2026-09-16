from django.urls import path
from . import views
app_name="appointments"
urlpatterns=[path("",views.index,name="index"),path("<int:pk>/cancel/",views.cancel,name="cancel"),path("<int:pk>/reschedule/",views.reschedule,name="reschedule")]
