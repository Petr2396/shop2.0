from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from accounts.models import Profile
from accounts.utils import normalize_phone


def get_or_create_user_by_phone(phone, password=None):
    phone = normalize_phone(phone)

    profile = Profile.objects.filter(phone=phone).select_related("user").first()

    if profile:
        user = profile.user
        if password and user.check_password(password):
            return user
        return None

    if not password:
        return None

    username = f"user_{phone.replace('+', '')}"

    user = User.objects.create_user(
        username=username,
        password=password
    )

    Profile.objects.create(
        user=user,
        phone=phone
    )

    return user
