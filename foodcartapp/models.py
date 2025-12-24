from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from collections import defaultdict

from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import Sum, F


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def get_total_price(self):
        return self.annotate(price=Sum(F('order_items__price') * F('order_items__quantity')))

    def annotate_available_restaurants(self):
        order_items = self.prefetch_related('order_items').values_list('id', 'order_items__product_id')
        order_to_product_ids = defaultdict(set)
        all_product_ids = set()

        for order_id, product_id in order_items:
            if product_id is not None:
                order_to_product_ids[order_id].add(product_id)
                all_product_ids.add(product_id)

        if not all_product_ids:
            for order in self:
                order.available_restaurant_ids = set()
            return self

        menu_items = (
            RestaurantMenuItem.objects.filter(
                product_id__in=all_product_ids,
                availability=True
            )
            .values_list('restaurant_id', 'product_id')
        )

        restaurant_to_products = defaultdict(set)
        for restaurant_id, product_id in menu_items:
            restaurant_to_products[restaurant_id].add(product_id)

        for order in self:
            required = order_to_product_ids.get(order.id, set())
            if not required:
                order.available_restaurant_ids = set()
                continue

            suitable_restaurants = set()
            for restaurant_id, products in restaurant_to_products.items():
                if required.issubset(products):
                    suitable_restaurants.add(restaurant_id)

            order.available_restaurant_ids = suitable_restaurants

        return self


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_TYPE = [
        ('electronic', 'электронно'),
        ('cash', 'наличными')
    ]

    firstname = models.CharField(
        'имя',
        max_length=100
    )
    lastname = models.CharField(
        'фамилия',
        max_length=100
    )
    phonenumber = PhoneNumberField(
        verbose_name='контактный телефон',
        region='RU',
        max_length=15,
        db_index=True
    )
    address = models.CharField(
        'адрес',
        max_length=250
    )
    status = models.CharField(
        'статус заказа',
        max_length=10,
        default='pending',
        choices=STATUS_CHOICES,
        db_index=True
    )
    comment = models.TextField(
        'комментарий к заказу',
        blank=True
    )
    registration_date = models.DateTimeField(
        'дата регистарции',
        default=timezone.now,
        db_index=True
    )
    called_date = models.DateTimeField(
        'дата звонка',
        blank=True,
        null=True,
        db_index=True
    )
    delivered_date = models.DateTimeField(
        'дата доставки',
        blank=True,
        null=True,
        db_index=True
    )
    payment_type = models.CharField(
        'вид оплаты',
        max_length=10,
        choices=PAYMENT_TYPE,
        db_index=True
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
        verbose_name="ресторан"
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f"{self.firstname} {self.lastname}"


def validate_quantity(value):
    if value <= 0:
        raise ValidationError(
            "количество не может быть равно нулю или быть отрицательным числом",
            params={'value': value},
        )


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='заказ'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='продукт',
    )
    quantity = models.IntegerField(
        verbose_name='количество продукта',
        validators=[validate_quantity]
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[validate_quantity]
    )

    class Meta:
        verbose_name = 'пункт заказа'
        verbose_name_plural = 'пункты заказа'

    def __str__(self):
        return f"{self.order.firstname} {self.order.lastname} {self.order.address}"
