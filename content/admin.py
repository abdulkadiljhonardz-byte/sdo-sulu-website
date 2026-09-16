from django.contrib import admin
from .models import Download, News, PublicPage, SiteSetting

admin.site.register([News, Download, PublicPage, SiteSetting])
