"""
URL configuration for lyncup project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import HttpResponse

#for JWT tokens: https://django-rest-framework-simplejwt.readthedocs.io/en/latest/getting_started.html
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from users.views.auth_views import VerifiedTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),

    #react app accesses api, so no need to render any index.html from django
    # path('', TemplateView.as_view(template_name='index.html')),

    path('', lambda request: HttpResponse("Welcome to the LyncUp API backend.", content_type="application/json")),

    #for JWT tokens: https://django-rest-framework-simplejwt.readthedocs.io/en/latest/getting_started.html
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/', VerifiedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/users/', include('users.urls')),
    path('chat/', include('chat.urls')),

]
