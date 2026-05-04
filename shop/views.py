from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Category
from django.contrib import messages

def index(request):
    """Главная страница"""
    products = Product.objects.filter(is_available=True)

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
    """Добавить товар в корзину (только для авторизованных)"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Сначала авторизируйтесь или зарегистрируйтесь, чтобы добавить товар в корзину')
        return redirect('accounts:login')

    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))

    if product.stock < quantity:
        messages.error(request, f'На складе только {product.stock} шт.')
        return redirect('shop:product_detail', slug=product.slug)

    # Уменьшаем остаток
    product.stock -= quantity
    product.save()

    # Добавляем в корзину
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += quantity
    else:
        cart[str(product_id)] = {
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
    if request.method == 'POST':
        new_quantity = int(request.POST.get('quantity', 1))
        cart = request.session.get('cart', {})
        pid_str = str(product_id)

        if pid_str in cart:
            old_quantity = cart[pid_str]['quantity']
            difference = new_quantity - old_quantity

            # Обновляем остаток на складе
            try:
                product = Product.objects.get(id=product_id)
                product.stock -= difference
                if product.stock < 0:
                    product.stock = 0
                product.save()
            except Product.DoesNotExist:
                pass

            cart[pid_str]['quantity'] = new_quantity
            request.session['cart'] = cart
            request.session.modified = True

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