from django.contrib import admin
from .models import Category, Tag, Product, Order, OrderItem, Review
from django.utils.html import format_html


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'gender', 'price', 'stock', 'is_available')
    list_filter = ('category', 'gender', 'is_available')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('tags',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status_colored', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id', 'address')
    readonly_fields = ('created_at', 'total_amount')
    actions = ['make_confirmed', 'make_shipped', 'make_delivered', 'make_cancelled']

    # Встроенная таблица товаров внутри заказа
    class OrderItemInline(admin.TabularInline):
        model = OrderItem
        extra = 0
        readonly_fields = ('product', 'quantity', 'price_at_purchase')
        can_delete = False

    inlines = [OrderItemInline]

    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'confirmed': 'blue',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Статус'

    # Действия массового изменения статуса
    def make_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, "Заказы отмечены как 'Подтверждён'")
    make_confirmed.short_description = "Отметить как Подтверждён"

    def make_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, "Заказы отмечены как 'Отправлен'")
    make_shipped.short_description = "Отметить как Отправлен"

    def make_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, "Заказы отмечены как 'Доставлен'")
    make_delivered.short_description = "Отметить как Доставлен"

    def make_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, "Заказы отменены")
    make_cancelled.short_description = "Отменить заказы"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price_at_purchase')
    list_filter = ('order__status',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')