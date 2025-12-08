"""web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.urls import path, re_path
from main.views import index
import main.track as tk


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', index),
    path('nearby', index),
    path('about', index),
    path('like', index),
    path('history/', tk.historyResponse),
    path('accurate/', tk.accurateResponse),
    path('rough/', tk.roughResponse),
    path('footprint/', tk.footprintResponse),
    path('delete/', tk.deleteVictimId),
    path('clear/', tk.clearFootprintCreater),
    path('nearby_proxy/', tk.nearbyResponse),
    path('member_proxy/', tk.memberProfileResponse)
]
