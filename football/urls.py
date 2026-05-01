from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    
    # Главная страница → редирект на логин (пока shop не трогаем)
    path('', lambda request: redirect('accounts:login'), name='home'),
]

# Обслуживание медиа-файлов (аватарки и т.д.)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)