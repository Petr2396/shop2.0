from django.contrib.auth import login 
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import UserForm, ProfileForm
from .forms import CustomUserCreationForm
from django.contrib.auth.views import LoginView
from accounts.models import Profile
from .services import get_or_create_user_by_phone
from django.contrib.auth.models import User



def phone_auth_view(request):
    phone = ""
    email = ""
    ask_password = False
    ask_email = False
    user_exists = False
    error_message = ""

    if request.method == "POST":
        phone = (request.POST.get("phone") or "").strip()
        password = (request.POST.get("password") or "").strip()
        email = (request.POST.get("email") or "").strip()

        if not phone:
            error_message = "Введите номер телефона"
            return render(request, "registration/login.html", {
                "phone": phone,
                "email": email,
                "ask_password": False,
                "ask_email": False,
                "user_exists": False,
                "error_message": error_message,
            })

        profile = Profile.objects.select_related("user").filter(phone=phone).first()

        if not password:
            user_exists = bool(profile)
            ask_password = True
            ask_email = not user_exists

            return render(request, "registration/login.html", {
                "phone": phone,
                "email": email,
                "ask_password": ask_password,
                "ask_email": ask_email,
                "user_exists": user_exists,
                "error_message": error_message,
            })

        if profile:
            user = authenticate(
                request,
                username=profile.user.username,
                password=password
            )
            if user:
                login(request, user)
                return redirect("home")

            error_message = "Неверный пароль"
            return render(request, "registration/login.html", {
                "phone": phone,
                "email": email,
                "ask_password": True,
                "ask_email": False,
                "user_exists": True,
                "error_message": error_message,
            })

        if not email:
            error_message = "Для регистрации укажите email"
            return render(request, "registration/login.html", {
                "phone": phone,
                "email": email,
                "ask_password": True,
                "ask_email": True,
                "user_exists": False,
                "error_message": error_message,
            })

        if User.objects.filter(email=email).exists():
            error_message = "Пользователь с таким email уже существует"
            return render(request, "registration/login.html", {
                "phone": phone,
                "email": email,
                "ask_password": True,
                "ask_email": True,
                "user_exists": False,
                "error_message": error_message,
            })

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )

        Profile.objects.create(
            user=user,
            phone=phone
        )

        login(request, user)
        return redirect("home")

    return render(request, "registration/login.html", {
        "phone": phone,
        "email": email,
        "ask_password": False,
        "ask_email": False,
        "user_exists": False,
        "error_message": error_message,
    })


#def phone_login_view(request):
    #if request.method == "POST":
        #phone = request.POST.get("phone")
        #password = request.POST.get("password")

        #if not phone or not password:
            #messages.error(request, "Введите телефон и пароль")
            #return redirect("login")

        #profile = Profile.objects.filter(phone=phone).select_related("user").first()

        #if not profile:
            #messages.error(request, "Пользователь не найден")
            #return redirect("login")

        #user = authenticate(
            #request,
            #username=profile.user.username,
            #password=password
        #)

        #if user:
            #login(request, user)
            #return redirect("accounts:profile")  # куда нужно
        #else:
            #messages.error(request, "Неверный пароль")

    #return render(request, "registration/login.html")


@login_required
def profile_view(request):
    profile = request.user.profile
    
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "accounts/profile.html", {"form": form})

@login_required
def edit_profile(request):
    user = request.user
    profile = user.profile

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Профиль успешно обновлён ✅")
            return redirect("accounts:profile")
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    return render(request, "accounts/edit_profile.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })


def signup_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/signup.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Просто меняем labels
        form.fields['username'].label = 'Логин'
        form.fields['password'].label = 'Пароль'
        return form