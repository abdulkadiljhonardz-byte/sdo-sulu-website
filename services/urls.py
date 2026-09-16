from django.urls import path
from . import views
app_name="services"
urlpatterns=[path("submit/",views.submit,name="submit"),path("track/",views.track,name="track"),path("attachment/<int:pk>/",views.attachment_download,name="attachment"),path("<str:tracking>/result/",views.result_download,name="result"),path("<str:tracking>/cancel/",views.cancel,name="cancel"),path("<str:tracking>/",views.detail,name="detail"),path("<str:tracking>/update/",views.update,name="update")]
