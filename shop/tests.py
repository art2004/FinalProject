from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from shop.models import Product, Category, Order
import uuid


class TestShopModels(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Мячи",
            slug=f"myachi-{uuid.uuid4().hex[:8]}"
        )
        self.product = Product.objects.create(
            name="Мяч Nike Merlin",
            slug=f"myach-nike-{uuid.uuid4().hex[:8]}",
            price=4500,
            stock=15,
            is_available=True,
            category=self.category,
            gender='unisex'
        )

    def test_product_create(self):
        self.assertEqual(self.product.name, "Мяч Nike Merlin")
        self.assertGreater(self.product.stock, 0)

    def test_product_stock_decrease(self):
        self.product.stock -= 3
        self.product.save()
        self.assertEqual(self.product.stock, 12)


class TestCart(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user(
            username=f'testcartuser_{uuid.uuid4().hex[:8]}',
            password='pass123'
        )
        self.client.force_login(self.user)

        self.category = Category.objects.create(
            name="Мячи",
            slug=f"myachi-{uuid.uuid4().hex[:8]}"
        )
        self.product = Product.objects.create(
            name="Мяч Nike Merlin",
            slug=f"myach-nike-{uuid.uuid4().hex[:8]}",
            price=4500,
            stock=10,
            is_available=True,
            category=self.category,
            gender='unisex'
        )

    def test_cart_add_positive(self):
        response = self.client.post(reverse('shop:cart_add', args=[self.product.id]), {'quantity': 2})
        self.assertEqual(response.status_code, 302)

        self.client.session.save()
        cart = self.client.session.get('cart', {})
        self.assertIn(str(self.product.id), cart)
        self.assertEqual(cart[str(self.product.id)]['quantity'], 2)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_cart_add_negative_out_of_stock(self):
        response = self.client.post(reverse('shop:cart_add', args=[self.product.id]), {'quantity': 20})
        self.assertEqual(response.status_code, 302)

    def test_cart_remove(self):
        self.client.post(reverse('shop:cart_add', args=[self.product.id]), {'quantity': 3})
        self.client.session.save()

        response = self.client.post(reverse('shop:cart_remove', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)

        self.client.session.save()
        cart = self.client.session.get('cart', {})
        self.assertNotIn(str(self.product.id), cart)

    def test_cart_update_quantity(self):
        self.client.post(reverse('shop:cart_add', args=[self.product.id]), {'quantity': 5})
        self.client.session.save()

        response = self.client.post(reverse('shop:cart_update', args=[self.product.id]), {'quantity': 3})
        self.assertEqual(response.status_code, 302)

        self.client.session.save()
        cart = self.client.session.get('cart', {})
        self.assertEqual(cart[str(self.product.id)]['quantity'], 3)


class TestOrders(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user(
            username=f'buyer_{uuid.uuid4().hex[:8]}',
            password='pass123'
        )
        self.client.force_login(self.user)

        self.category = Category.objects.create(
            name="Мячи",
            slug=f"myachi-{uuid.uuid4().hex[:8]}"
        )
        self.product1 = Product.objects.create(
            name="Мяч", slug=f"myach-{uuid.uuid4().hex[:8]}",
            price=4500, stock=10,
            category=self.category, gender='unisex'
        )
        self.product2 = Product.objects.create(
            name="Футболка", slug=f"futbolka-{uuid.uuid4().hex[:8]}",
            price=2500, stock=5,
            category=self.category, gender='male'
        )

        session = self.client.session
        session['cart'] = {
            str(self.product1.id): {'quantity': 2, 'price': 4500},
            str(self.product2.id): {'quantity': 1, 'price': 2500}
        }
        session.save()

    def test_checkout_creates_order(self):
        response = self.client.post(reverse('shop:checkout'), {
            'address': 'Москва, ул. Ленина 10',
            'phone': '+79161234567'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.filter(user=self.user).exists())


class TestProductViews(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(
            name="Мячи",
            slug=f"myachi-{uuid.uuid4().hex[:8]}"
        )
        self.product = Product.objects.create(
            name="Мяч Nike Merlin",
            slug=f"myach-nike-{uuid.uuid4().hex[:8]}",
            price=4500,
            stock=10,
            is_available=True,
            category=self.category,
            gender='unisex'
        )

    def test_product_detail_page(self):
        response = self.client.get(reverse('shop:product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_search_positive(self):
        response = self.client.get(reverse('shop:search') + '?q=мяч')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Мяч Nike Merlin")

    def test_search_negative(self):
        response = self.client.get(reverse('shop:search') + '?q=неизвестныйтовар12345')
        self.assertEqual(response.status_code, 200)
        # Можно проверить, что товаров нет или есть сообщение "ничего не найдено"