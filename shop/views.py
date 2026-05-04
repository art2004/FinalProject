from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Category
from django.contrib import messages

def index(request):
    """Главная страница магазина"""
    products = Product.objects.filter(is_available=True)[:12]
    categories = Category.objects.all()
    return render(request, 'shop/index.html', {
        'products': products,
        'categories': categories
    })


def product_detail(request, slug):
    """Детальная страница товара"""
    product = get_object_or_404(Product, slug=slug, is_available=True)
    return render(request, 'shop/product_detail.html', {'product': product})


def category_products(request, slug):
    """Товары по категории"""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_available=True)
    return render(request, 'shop/category_products.html', {
        'category': category,
        'products': products
    })

# ====================== КОРЗИНА ======================

def cart_add(request, product_id):
    """Добавить товар в корзину и остаться на странице товара"""
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))

    if product.stock < quantity:
        messages.error(request, f'На складе только {product.stock} шт.')
        return redirect('shop:product_detail', slug=product.slug)

    product.stock -= quantity
    product.save()

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
    return redirect('shop:product_detail', slug=product.slug)   # ← остаёмся на товаре


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