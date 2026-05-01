from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Введите корректный номер телефона")]
    )
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)


    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name="Аватарка"
    )
    favorite_team = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Любимая команда"
    )
    shirt_size = models.CharField(
        max_length=5,
        choices=[
            ('XS', 'XS'), ('S', 'S'), ('M', 'M'),
            ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL')
        ],
        blank=True,
        verbose_name="Размер формы"
    )
    favorite_player = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Любимый игрок"
    )

    latitude = models.FloatField(null=True, blank=True, verbose_name="Широта")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Долгота")

    def __str__(self):
        return f"Profile of {self.user.username}"

    # Кастомная валидация (будет использоваться позже)
    def clean(self):
        if self.phone and not self.phone.startswith('+'):
            self.phone = '+' + self.phone