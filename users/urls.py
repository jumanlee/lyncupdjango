from django.urls import path
from django.views.generic import TemplateView
from . import views

#note juman, change all of these to DefaultRouter()

#Code written by me
urlpatterns = [
    path('register/', views.Register.as_view(), name='register_api'),
    path('like/', views.LikeView.as_view(), name='like_api'),
    path('unlike/', views.UnlikeView.as_view(), name='unlike_api'),
    path("updateprofile/", views.UpdateProfileView.as_view(), name='updateprofile_api')

]

#my code ends here