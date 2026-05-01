from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
from datetime import date
from django.core.exceptions import ValidationError


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email


class ProfileForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        input_formats=['%Y-%m-%d', '%d.%m.%Y'],  # важно!
        label="Дата рождения"
    )

    class Meta:
        model = Profile
        fields = [
            'avatar', 'phone', 'address', 'date_of_birth',
            'favorite_team', 'shirt_size', 'favorite_player',
            'latitude', 'longitude'
        ]
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'favorite_team': forms.TextInput(attrs={'class': 'form-control'}),
            'shirt_size': forms.Select(attrs={'class': 'form-control'}),
            'favorite_player': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()

            if dob > today:
                raise ValidationError("Дата рождения не может быть в будущем!")

            if dob.year < 1900:
                raise ValidationError("Дата рождения не может быть раньше 1900 года")

            age = today.year - dob.year
            if age > 120:
                raise ValidationError("Дата рождения выглядит нереалистично (максимальный возраст — 120 лет)")

        return dob