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

        try_to_solve_impolite_to_polite_on_new_tabs(request_body)

        send_event('testchannel', 'message', message_to_send)
        return HttpResponse("ok")

last_impolite_offer_message = {"obj": None}
def try_to_solve_impolite_to_polite_on_new_tabs(request_body):
    user = request_body['user']
    received_offer = json.dumps(request_body['sdp'])
    message_to_send = {"sdp": received_offer, "user": user}
    is_offer = request_body['sdp']['type'] == "offer"
    if user == "impolite" and is_offer:
        last_impolite_offer_message['obj'] = message_to_send
    if user == "polite" and is_offer and last_impolite_offer_message['obj'] is not None:
        # the polite peer connected, 
        send_event('testchannel', 'message', last_impolite_offer_message['obj'])
        last_impolite_offer_message['obj'] = None

def home(request, user):
    return render(request, 'mainapp/index.html', {"user": user})