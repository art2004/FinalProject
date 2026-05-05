from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistrationForm, ProfileForm
from .models import Profile
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from shop.models import Order, OrderItem, Product

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)

            from django.contrib.auth.models import Group
            customer_group = Group.objects.get(name='Customer')
            user.groups.add(customer_group)

            login(request, user)
            messages.success(request, 'Регистрация прошла успешно! Добро пожаловать в магазин!')
            return redirect('shop:index')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})



def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('shop:index')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def user_logout(request):
    """Выход из аккаунта + возврат товаров из корзины на склад"""
    cart = request.session.get('cart', {})

    if cart:
        for pid_str, item in cart.items():
            try:
                product = Product.objects.get(id=int(pid_str))
                product.stock += item['quantity']
                product.save()
            except Product.DoesNotExist:
                pass

        # Очищаем корзину
        request.session['cart'] = {}
        request.session.modified = True

    logout(request)
    messages.success(request, 'Вы успешно вышли из аккаунта. Товары из корзины возвращены на склад.')
    return redirect('shop:index')

@login_required
def profile(request):

    try:
        profile = request.user.profile
    except:
        profile = None

    # Получаем все заказы пользователя
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'orders': orders,
        'role': 'Manager' if request.user.groups.filter(name='Manager').exists() else 'Customer',
        'role_class': 'bg-success' if request.user.groups.filter(name='Manager').exists() else 'bg-primary',
    })


@login_required
def edit_profile(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'accounts/edit_profile.html', {
        'form': form,
        'profile': profile
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # чтобы не разлогинивало
            messages.success(request, 'Пароль успешно изменён!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})