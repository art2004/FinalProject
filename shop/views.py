from django.shortcuts import render, get_object_or_404
from .models import Product, Category


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
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'shop/product_detail.html', {'product': product})


def category_products(request, slug):
    """Товары по категории"""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_available=True)
    return render(request, 'shop/category_products.html', {
        'category': category,
        'products': products
    })