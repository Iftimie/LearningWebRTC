from django.urls import path
from . import views
from django.conf.urls import include
import django_eventstream


urlpatterns = [
    path('offer', views.offer, name='offer'),
    path('answer', views.answer, name='answer'),
    path('clear', views.clear, name='clear'),
    path('events/', include(django_eventstream.urls), {
        'channels': ['testchannel']
    }),
    path('home/<user>', views.home, name='home'),
]