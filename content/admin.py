from django.contrib import admin
from .models import Download, HomepageSlide, News, PublicPage, SiteSetting

admin.site.register([News, Download, HomepageSlide, PublicPage, SiteSetting])
