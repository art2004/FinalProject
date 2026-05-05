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
from shop.models import Product
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            Profile.objects.get_or_create(user=user)

            customer_group = Group.objects.get(name='Customer')
            user.groups.add(customer_group)

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            activation_link = request.build_absolute_uri(
                f"/accounts/activate/{uid}/{token}/"
            )

            subject = 'Подтверждение регистрации — Football Shop'
            message = render_to_string('accounts/email_activation.html', {
                'user': user,
                'activation_link': activation_link,
            })

            send_mail(
                subject=subject,
                message='',
                from_email=None,
                recipient_list=[user.email],
                html_message=message,
                fail_silently=False,
            )

            logger.info(f"Регистрация начата. Письмо с подтверждением отправлено: {user.username} ({user.email})")
            messages.success(request, 'Регистрация прошла успешно! Проверьте почту и подтвердите email.')
            return redirect('accounts:login')
        else:
            # Красивое логирование ошибок (без HTML)
            error_list = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_list.append(f"{field}: {error}")
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
            username = request.POST.get('username', '')
            logger.warning(f"Неудачная попытка входа: {username}")
            messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def user_logout(request):
    if request.user.is_authenticated:
        logger.info(f"Выход пользователя: {request.user.username} (ID: {request.user.id})")

    cart = request.session.get('cart', {})
    if cart:
        for pid_str, item in cart.items():
            try:
                product = Product.objects.get(id=int(pid_str))
                product.stock += item['quantity']
                product.save()
            except Product.DoesNotExist:
                pass

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
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменён!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


def activate_account(request, uidb64, token):
    """Активация аккаунта по ссылке из письма"""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        logger.info(f"Регистрация завершена успешно: {user.username} (ID: {user.id})")
        messages.success(request, 'Email успешно подтверждён! Теперь вы можете войти.')
        return redirect('accounts:login')
    else:
        logger.warning(f"Неудачная попытка активации аккаунта (uidb64={uidb64})")
        messages.error(request, 'Ссылка для активации недействительна или устарела.')
        return redirect('accounts:register')