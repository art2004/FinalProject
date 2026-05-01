from django.urls import path
from django.views.generic import RedirectView

app_name = 'shop'

urlpatterns = [
    path('', RedirectView.as_view(url='/accounts/login/'), name='index'),  # временно
]