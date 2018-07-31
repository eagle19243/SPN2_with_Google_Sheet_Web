# -*- coding: utf-8 -*-
from django.shortcuts import render

# Create your views here.
def index(request):
    if request.method == 'POST':
        print(request.POST['google_sheet_url']);

        return render(request, "index.html")
    else:
        return render(request, "index.html")
