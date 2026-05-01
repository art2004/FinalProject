from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistrationForm, ProfileForm
from .models import Profile
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Создаём Profile автоматически
            Profile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('shop:index')  # потом поменяем на главную магазина
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('shop:index')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    return render(request, 'accounts/login.html')

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из аккаунта')
    return redirect('shop:index')