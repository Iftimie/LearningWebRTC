from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django_eventstream import send_event
from django.http.response import HttpResponse
import json
import time

"""
Request body contains:
sdp
user
"""

@csrf_exempt
def sdp(request):
    if request.method == "POST":
        send_event('testchannel', 'message', json.loads(request.body))
        return HttpResponse("ok")

def home(request, user):
    return render(request, 'mainapp/index.html', {"user": user})