from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistrationForm, ProfileForm
from .models import Profile
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from shop.models import Order, Product
import logging

logger = logging.getLogger(__name__)


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True          # сразу активен, без подтверждения email
            user.save()

            Profile.objects.get_or_create(user=user)

            # Добавляем пользователя в группу Customer
            customer_group = Group.objects.get_or_create(name='Customer')[0]
            user.groups.add(customer_group)

            logger.info(f"Регистрация прошла успешно: {user.username} ({user.email})")
            messages.success(request, 'Регистрация прошла успешно! Теперь вы можете войти в аккаунт.')
            return redirect('accounts:login')
        else:
            error_list = [f"{field}: {error}" for field, errors in form.errors.items() for error in errors]
            logger.warning(f"Неудачная регистрация: {' | '.join(error_list)}")
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"Вход выполнен: {user.username} (ID: {user.id})")
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('shop:index')
        else:
            logger.warning(f"Неудачная попытка входа: {request.POST.get('username')}")
            messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def user_logout(request):
    """Выход из аккаунта + возврат товаров из корзины на склад"""
    cart = request.session.get('cart', {})
    username = request.user.username
    user_id = request.user.id

    if cart:
        returned_items = []
        for pid_str, item in cart.items():
            try:
                product = Product.objects.get(id=int(pid_str))
                product.stock += item['quantity']
                product.save()
                returned_items.append(f"{item['quantity']} шт. '{product.name}'")
            except Product.DoesNotExist:
                pass

        if returned_items:
            logger.info(
                f"Выход пользователя {username} (ID: {user_id}). "
                f"Возвращено на склад: {', '.join(returned_items)}"
            )
        else:
            logger.info(f"Выход пользователя {username} (ID: {user_id}) — корзина была пуста")
    else:
        logger.info(f"Выход пользователя {username} (ID: {user_id})")

    request.session['cart'] = {}
    request.session.modified = True

    logout(request)
    messages.success(request, 'Вы успешно вышли из аккаунта. Товары из корзины возвращены на склад.')
    return redirect('shop:index')


@login_required
def profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = None

    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    logger.info(f"Пользователь {request.user.username} открыл профиль (заказов: {orders.count()})")

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
            logger.info(f"Пользователь {request.user.username} обновил профиль")
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
            update_session_auth_hash(request, user)
            logger.info(f"Пользователь {request.user.username} успешно сменил пароль")
            messages.success(request, 'Пароль успешно изменён!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})