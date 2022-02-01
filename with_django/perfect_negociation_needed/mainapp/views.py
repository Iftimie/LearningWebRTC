from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django_eventstream import send_event
from django.http.response import HttpResponse
import json

@csrf_exempt
def sdp(request):
    if request.method == "POST":
        request_body = json.loads(request.body)
        received_offer = json.dumps(request_body['sdp'])
        user = request_body['user']
        message_to_send = {"sdp": received_offer, "user": user}

        send_event('testchannel', 'message', message_to_send)
        return HttpResponse("ok")

def home(request, user):
    return render(request, 'mainapp/index.html', {"user": user})