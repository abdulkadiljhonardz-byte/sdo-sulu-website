from django.urls import path

from . import views

app_name = "pages"
urlpatterns = [
    path("mission-and-vision/", views.mission_vision, name="mission_vision"),
    path("contact/", views.contact_page, name="contact"),
    path("<slug:slug>/", views.public_page, name="detail"),
]
