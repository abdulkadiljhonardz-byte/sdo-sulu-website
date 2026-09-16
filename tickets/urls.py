from django.urls import path
from . import views
app_name="tickets"
urlpatterns=[path("",views.index,name="index"),path("attachment/<int:pk>/",views.attachment,name="attachment"),path("<int:pk>/",views.detail,name="detail")]
