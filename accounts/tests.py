from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from accounts.models import Profile
import uuid


class TestAuth(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.customer_group, _ = Group.objects.get_or_create(name='Customer')

    def test_registration_positive(self):
        username = f'testuser_{uuid.uuid4().hex[:8]}'
        data = {
            'username': username,
            'email': f'{username}@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        response = self.client.post(reverse('accounts:register'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username=username).exists())

    def test_registration_negative_duplicate(self):
        username = f'testuser_{uuid.uuid4().hex[:8]}'
        User.objects.create_user(username=username, password='pass123')
        data = {
            'username': username,
            'email': f'{username}@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        response = self.client.post(reverse('accounts:register'), data)
        self.assertEqual(response.status_code, 200)

    def test_login_positive(self):
        username = f'loginuser_{uuid.uuid4().hex[:8]}'
        User.objects.create_user(username=username, password='StrongPass123!')
        response = self.client.post(reverse('accounts:login'), {
            'username': username,
            'password': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_negative_wrong_password(self):
        username = f'loginuser_{uuid.uuid4().hex[:8]}'
        User.objects.create_user(username=username, password='StrongPass123!')
        response = self.client.post(reverse('accounts:login'), {
            'username': username,
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        username = f'logoutuser_{uuid.uuid4().hex[:8]}'
        user = User.objects.create_user(username=username, password='pass123')
        self.client.force_login(user)
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class TestProfile(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user(
            username=f'profileuser_{uuid.uuid4().hex[:8]}',
            password='pass123',
            email='profile@example.com'
        )
        self.client.force_login(self.user)

        # ←←← КРИТИЧНО: явно создаём Profile
        Profile.objects.create(user=self.user)

    def test_profile_page_access(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_edit_profile_positive(self):
        data = {
            'phone': '+79161234567',
            'date_of_birth': '2000-05-15',
            'favorite_team': 'Спартак Москва',
            'shirt_size': 'M',
            'favorite_player': 'Месси',
        }
        response = self.client.post(reverse('accounts:edit_profile'), data)
        self.assertEqual(response.status_code, 302)

        # Проверяем, что данные действительно сохранились
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '+79161234567')
        self.assertEqual(self.user.profile.favorite_team, 'Спартак Москва')