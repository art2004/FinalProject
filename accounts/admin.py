from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from .models import Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'

class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'is_staff', 'get_role')
    list_filter = ('groups', 'is_staff')

    def get_role(self, obj):
        if obj.groups.filter(name='Manager').exists():
            return "Менеджер"
        elif obj.groups.filter(name='Customer').exists():
            return "Покупатель"
        return "—"
    get_role.short_description = 'Роль'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Profile)