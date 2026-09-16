from django.urls import path

from . import views

app_name = "pages"
urlpatterns = [path("<slug:slug>/", views.public_page, name="detail")]
