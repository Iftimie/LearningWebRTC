from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.conf.urls import include
import django_eventstream


urlpatterns = [
    path('sdp', views.sdp, name='sdp'),
    path('events/', include(django_eventstream.urls), {
        'channels': ['testchannel']
    }),
    path('home/<user>', views.home, name='home'),
]