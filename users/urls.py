from django.urls import path
from django.views.generic import TemplateView
from users.app_func import app_views 
from users.aux_func import aux_views
from users.chat_func import chat_views
from users.auth_func import auth_views

#note juman, change all of these to DefaultRouter()

urlpatterns = [
    path("testapi/", aux_views.TestApi.as_view(), name='testapi_api'),
    path('register/', auth_views.Register.as_view(), name='register_api'),
    path("verify-email/<uidb64>/<token>/", auth_views.VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", auth_views.ResendVerificationView.as_view(), name="resend-verification"),
    path("send-password-reset/", auth_views.SendPasswordResetView.as_view(), name="send-password-reset"),
    path("reset-password/<uidb64>/<token>/", auth_views.ResetPasswordView.as_view(), name="reset-password"),
    path('change-password-authenticated/', auth_views.ChangePasswordAuthenticatedView.as_view(), name='change-password-authenticated'),


    path('like/', chat_views.LikeView.as_view(), name='like_api'),
    path('unlike/', chat_views.UnlikeView.as_view(), name='unlike_api'),
    path("checkprofilecomplete/", app_views.CheckProfileCompleteView.as_view(), name='checkprofilecomplete_api'),
    path("updateprofile/", app_views.UpdateProfileView.as_view(), name='updateprofile_api'),
    path("showprofile/<int:appuser_id>/", app_views.ShowProfileView.as_view(), name='showprofile_api'),
    path("searchorg/", app_views.SearchOrgView.as_view(), name='searchorg_api'),
    path("showmultiprofiles/", app_views.ShowMultiProfilesView.as_view(), name='showmultiprofiles_api'),
    path("showrequests/", app_views.ShowSentRequestsView.as_view(), name='showrequests_api'),
    path("showallcountries/", app_views.ShowAllCountriesView.as_view(), name='showallcountries_api'),
]

#my code ends here