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

    def __str__(self):
        return f"Profile of {self.user.username}"

    # Кастомная валидация (будет использоваться позже)
    def clean(self):
        if self.phone and not self.phone.startswith('+'):
            self.phone = '+' + self.phone