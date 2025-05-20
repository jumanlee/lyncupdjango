from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings

#if expect high traffic, could use Celery: just wrap the send_mail call in a celery task. Nothing else changes.) But for now, we don't need to.
def send_verification_email(user):
    #uid is user ID, but safely encoded in base64 so it can be used in a URL
    #Base64 is a way to convert any data (like a number, text, or file) into a string made only of A–Z, a–z, 0–9, +, /
    #note that user.pk is always the primary-key value of the instance, no matter what we've named that field. pk is just a built-in alias for the primary key field, whatever it is. In AppUser model it's declared id = models.BigAutoField(primary_key=True), so, user.pk == user.id (an auto-incrementing int), if one day we swapped the PK to a UUID (or anything else) user.pk would still “just work”, so leave the line exactly as it is
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    #we don't use JWT token here, as the user is not yet authenticated, we use a default token
    token = default_token_generator.make_token(user)

    verify_link = f"{settings.BACKEND_VERIFY_URL}/{uid}/{token}"

    subject = "Verify your email"
    message = (
        f"Hi {user.firstname},\n\n"
        f"Thanks for signing up to LyncUp.\n"
        f"Click the link below to activate your account:\n\n"
        f"{verify_link}\n\n"
        "If you didn't create this account, ignore this email."
    )

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )

def send_password_reset(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    reset_link = f"{settings.FRONTEND_RESET_PASSWORD_URL}/{uid}/{token}"

    subject = "Reset your password"
    message = (
        f"Hi {getattr(user, 'first_name', user.email)},\n\n"
        "You requested a password reset. Click the link below:\n\n"
        f"{reset_link}\n\n"
        "If you didn’t ask for this, just ignore this email."
    )
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)

