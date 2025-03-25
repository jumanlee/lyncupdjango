from django.urls import path
from django.views.generic import TemplateView
from . import views

#note juman, change all of these to DefaultRouter()

urlpatterns = [
    path("testapi/", views.TestApi.as_view(), name='testapi_api'),
    path('register/', views.Register.as_view(), name='register_api'),
    path('like/', views.LikeView.as_view(), name='like_api'),
    path('unlike/', views.UnlikeView.as_view(), name='unlike_api'),
    path("updateprofile/", views.UpdateProfileView.as_view(), name='updateprofile_api'),
    path("showprofile/<int:appuser_id>/", views.ShowProfileView.as_view(), name='showprofile_api'),
    path("searchorg/", views.SearchOrgView.as_view(), name='searchorg_api'),
    path("showmultiprofiles/", views.ShowMultiProfilesView.as_view(), name='showmultiprofiles_api'),
]

#my code ends here