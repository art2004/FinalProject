from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem, Product
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail

def index(request):
    """Главная страница"""
    products = Product.objects.filter(is_available=True)


    only_in_stock = request.GET.get('in_stock') == '1'
    if only_in_stock:
        products = products.filter(stock__gt=0)

    # Фильтр по цене
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Сортировка
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'name':
        products = products.order_by('name')

    return render(request, 'shop/index.html', {
        'products': products,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
        'only_in_stock': only_in_stock,
    })


def product_detail(request, slug):
    """Детальная страница товара"""
    product = get_object_or_404(Product, slug=slug, is_available=True)
    return render(request, 'shop/product_detail.html', {'product': product})


def category_products(request, slug):
    """Страница категории"""
    gender_map = {
        'male': 'Мужское',
        'female': 'Женское',
        'kids': 'Детское',
        'unisex': 'Унисекс / Инвентарь'
    }

    products = Product.objects.filter(is_available=True, gender=slug)

    # === ФИЛЬТР "ТОЛЬКО В НАЛИЧИИ" ===
    only_in_stock = request.GET.get('in_stock') == '1'
    if only_in_stock:
        products = products.filter(stock__gt=0)

    # Фильтр по цене
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Сортировка
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'name':
        products = products.order_by('name')

    return render(request, 'shop/category_products.html', {
        'products': products,
        'category_name': gender_map.get(slug, 'Категория'),
        'gender_slug': slug,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
        'only_in_stock': only_in_stock,
    })


def search(request):
    """Простой и надёжный поиск (работает с русскими буквами в любом регистре)"""
    query = request.GET.get('q', '').strip().lower()  # приводим запрос к нижнему регистру

    # Берём все доступные товары
    products = Product.objects.filter(is_available=True)

    if query:
        # Фильтруем на стороне Python — 100% работает с кириллицей
        filtered = []
        for product in products:
            name_lower = product.name.lower()
            desc_lower = product.description.lower() if product.description else ""
            if query in name_lower or query in desc_lower:
                filtered.append(product)

        products = filtered

    return render(request, 'shop/search_results.html', {
        'products': products,
        'query': request.GET.get('q', '').strip()  # оригинальный запрос для отображения
    })

# ====================== КОРЗИНА ======================

def cart_add(request, product_id):
    """Добавить товар в корзину — с жёсткой проверкой остатка"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Сначала авторизируйтесь или зарегистрируйтесь')
        return redirect('accounts:login')

    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))

    # ЖЁСТКАЯ ПРОВЕРКА
    if quantity > product.stock:
        messages.error(request, f'На складе только {product.stock} шт. Вы не можете добавить больше.')
        return redirect('shop:product_detail', slug=product.slug)

    if quantity < 1:
        messages.error(request, 'Количество должно быть минимум 1')
        return redirect('shop:product_detail', slug=product.slug)

    # Уменьшаем остаток на складе
    product.stock -= quantity
    product.save()

    # Добавляем в корзину
    cart = request.session.get('cart', {})
    pid_str = str(product_id)

    if pid_str in cart:
        cart[pid_str]['quantity'] += quantity
    else:
        cart[pid_str] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': quantity,
            'image': product.image.url if product.image else None
        }

    request.session['cart'] = cart
    request.session.modified = True

    messages.success(request, f'{product.name} добавлен в корзину')
    return redirect('shop:product_detail', slug=product.slug)


def cart_update(request, product_id):
    """Изменить количество товара в корзине"""
    if request.method != 'POST':
        return redirect('shop:cart')

    new_quantity = int(request.POST.get('quantity', 1))
    cart = request.session.get('cart', {})
    pid_str = str(product_id)

    if pid_str not in cart:
        return redirect('shop:cart')

    old_quantity = cart[pid_str]['quantity']
    difference = new_quantity - old_quantity

    if new_quantity < 1:
        messages.error(request, 'Количество должно быть минимум 1')
        return redirect('shop:cart')

    # Проверка остатка при увеличении количества
    if difference > 0:
        try:
            product = Product.objects.get(id=product_id)
            if difference > product.stock:
                messages.error(request, f'На складе только {product.stock} шт.')
                return redirect('shop:cart')
            product.stock -= difference
            product.save()
        except Product.DoesNotExist:
            pass

    # При уменьшении — возвращаем на склад
    elif difference < 0:
        try:
            product = Product.objects.get(id=product_id)
            product.stock += abs(difference)
            product.save()
        except Product.DoesNotExist:
            pass

    # Обновляем количество в корзине
    cart[pid_str]['quantity'] = new_quantity
    request.session['cart'] = cart
    request.session.modified = True

    messages.success(request, 'Количество обновлено')
    return redirect('shop:cart')

def cart_remove(request, product_id):
    """Удалить товар из корзины"""
    cart = request.session.get('cart', {})
    pid_str = str(product_id)

    if pid_str in cart:
        quantity = cart[pid_str]['quantity']
        try:
            product = Product.objects.get(id=product_id)
            product.stock += quantity
            product.save()
        except Product.DoesNotExist:
            pass

        del cart[pid_str]
        request.session['cart'] = cart
        request.session.modified = True

    return redirect('shop:cart')

def cart(request):
    """Просмотр корзины"""
    cart_items = request.session.get('cart', {})
    total = 0.0

    # Добавляем subtotal для каждого товара
    for pid, item in cart_items.items():
        price = float(item['price'])
        quantity = item['quantity']
        item['subtotal'] = round(price * quantity, 2)
        total += item['subtotal']

    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total': round(total, 2)
    })


@login_required
def checkout(request):
    """Оформление заказа + отправка письма на почту"""
    cart = request.session.get('cart', {})

    if not cart:
        messages.warning(request, 'Корзина пуста')
        return redirect('shop:cart')

    # Подсчёт итоговой суммы
    total = 0
    for item in cart.values():
        price = float(item['price'])
        quantity = item['quantity']
        item['subtotal'] = round(price * quantity, 2)
        total += item['subtotal']

    if request.method == 'POST':
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        comment = request.POST.get('comment', '')

        if not address or not phone:
            messages.error(request, 'Укажите адрес и телефон')
            return redirect('shop:checkout')

        # Создаём заказ
        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            address=address,
            phone=phone,
            comment=comment,
            status='pending'
        )

        # Добавляем товары в заказ
        for pid_str, item in cart.items():
            product = Product.objects.get(id=int(pid_str))
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                price_at_purchase=float(item['price'])
            )

        # Очищаем корзину
        request.session['cart'] = {}
        request.session.modified = True

        # === ОТПРАВКА ПИСЬМА ===
        try:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string

            subject = f'Заказ #{order.id} успешно оформлен — Football Shop'

            html_message = render_to_string('shop/email_order_confirmation.html', {
                'order': order,
                'user': request.user,
                'items': order.items.all(),
                'total': total,
            })

            send_mail(
                subject=subject,
                message='',
                from_email=None,
                recipient_list=[request.user.email],
                html_message=html_message,
                fail_silently=False,
            )
            messages.success(request, f'Заказ #{order.id} оформлен! Письмо отправлено на вашу почту.')
        except Exception as e:
            messages.warning(request, f'Заказ #{order.id} оформлен, но письмо отправить не удалось.')

        return redirect('accounts:profile')

    # Данные из профиля для автозаполнения
    try:
        profile = request.user.profile
        initial_address = profile.address or ''
        initial_phone = profile.phone or ''
    except:
        initial_address = ''
        initial_phone = ''

    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'total': round(total, 2),
        'initial_address': initial_address,
        'initial_phone': initial_phone,
    })

@login_required
def order_detail(request, order_id):
    """Детальная страница заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Добавляем subtotal для каждого товара
    for item in order.items.all():
        item.subtotal = round(float(item.price_at_purchase) * item.quantity, 2)

    return render(request, 'shop/order_detail.html', {
        'order': order,
    })

@login_required
def cancel_order(request, order_id):
    """Отмена заказа пользователем"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != 'pending':
        messages.error(request, 'Только заказы в статусе "В обработке" можно отменить.')
        return redirect('shop:order_detail', order_id=order.id)

    # Возвращаем товары на склад
    for item in order.items.all():
        try:
            product = item.product
            product.stock += item.quantity
            product.save()
        except:
            pass

    order.status = 'cancelled'
    order.save()

    messages.success(request, f'Заказ #{order.id} успешно отменён. Товары возвращены на склад.')
    return redirect('accounts:profile')


@receiver(post_save, sender=Order)
def send_status_notification(sender, instance, created, **kwargs):
    """Отправляем письмо пользователю при изменении статуса заказа"""
    if created:
        return  # новое создание заказа уже обрабатывается в checkout

    # Отправляем только если статус изменился
    if hasattr(instance, '_status_changed') and instance._status_changed:
        try:
            send_mail(
                subject=f'Обновление статуса заказа #{instance.id} — Football Shop',
                message=f'''
Здравствуйте!

Статус вашего заказа #{instance.id} изменён на: **{instance.get_status_display()}**

Дата изменения: {instance.created_at|date:"d.m.Y H:i"}

Перейдите в личный кабинет, чтобы посмотреть подробности.

С уважением,
Команда Football Shop
                ''',
                from_email=None,
                recipient_list=[instance.user.email],
                fail_silently=True,
            )
        except:
            pass