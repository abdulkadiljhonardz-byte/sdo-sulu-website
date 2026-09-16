from django.shortcuts import render
from .models import Vacancy
def index(request): return render(request,"vacancies/list.html",{"items":Vacancy.objects.filter(status="OPEN")})
