from django.urls import path
from django.views.generic import TemplateView
from . import views

#note juman, change all of these to DefaultRouter()

#Code written by me
urlpatterns = [
    path('api/users/register/', views.Register.as_view(), name='register_api'),

    #don't need to include the user ID of the sender in the url for this addfriend endpoint. The sender is already authenticated, so can easily get their user id directly from the request inside your API logic, like what I have already done with request.user.id in views.py
    path('api/addfriend/', views.AddFriend.as_view(), name='addfriend_api'),
    path('api/acceptrequest/', views.AcceptRequest.as_view(), name='acceptrequest_api'),
    path('api/declinerequest/', views.DeclineRequest.as_view(), name='declinerequest_api'),
    path('api/friendlist/', views.FriendList.as_view(), name='friendlist_api'),
    path('api/searchuser/', views.SearchUser.as_view(), name='searchuser_api'),
    path('api/updatestatus/', views.UpdateStatus.as_view(), name='updatestatus_api'),
    path('api/updatebio/', views.UpdateBio.as_view(), name='updatebio_api'),
    path('api/getfriendprofile/<int:pk>/', views.GetFriendProfile.as_view(), name='getfriendprofile_api'),
    path('api/getownprofile/', views.GetOwnProfile.as_view(), name='getownprofile_api'),
    path('api/getrequestlist/', views.GetAddRequestList.as_view(), name='getrequestlist_api'),

]

#my code ends here