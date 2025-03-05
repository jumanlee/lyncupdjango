from django.urls import path
from django.views.generic import TemplateView
from . import views

#note juman, change all of these to DefaultRouter()

urlpatterns = [
    path('register/', views.Register.as_view(), name='register_api'),
    path('like/', views.LikeView.as_view(), name='like_api'),
    path('unlike/', views.UnlikeView.as_view(), name='unlike_api'),
    path("updateprofile/", views.UpdateProfileView.as_view(), name='updateprofile_api'),
    path("showprofile/<int:appuser_id>/", views.ShowProfileView.as_view(), name='showeprofile_api'),
    path("testapi/", views.TestApi.as_view(), name='testapi_api')

]

#my code ends here