from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django_eventstream import send_event
from django.http.response import HttpResponse
import json

storage = {
    "user1_chat_offer": '""',
    "user2_chat_offer": '""'
}

@csrf_exempt
def offer(request):
    if request.method == "POST":
        request_body = json.loads(request.body)
        received_offer = json.dumps(request_body['offer'])
        user = request_body['user']
        if "user1" == user:
            storage["user1_chat_offer"] = received_offer
            returned_offer = storage["user2_chat_offer"]
        else:
            storage["user2_chat_offer"] = received_offer
            returned_offer = storage["user1_chat_offer"]
        peer_offer_sdp = json.loads(returned_offer)
        return JsonResponse({'offer': peer_offer_sdp})

@csrf_exempt
def answer(request):
    if request.method == "POST":
        request_body = json.loads(request.body)
        send_event('testchannel', 'message', request_body['answer'])
        return HttpResponse("ok")

@csrf_exempt
def clear(request):
    if request.method == "POST":
        storage["user1_chat_offer"] = '""'
        storage["user2_chat_offer"] = '""'
        return HttpResponse("ok")

def home(request, user):
    return render(request, 'mainapp/index.html', {"user": user})
