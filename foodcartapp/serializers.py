from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from foodcartapp.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']

    def validate_quantity(self, value):
        if value <= 0:
            raise ValidationError("Количество не может быть равно нулю или быть отрицательным числом")
        return value


class OrderSerializer(serializers.ModelSerializer):
    products = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'products', 'firstname', 'lastname', 'phonenumber', 'address']

    def validate_products(self, value):
        if not value:
            raise ValidationError("Это поле не может быть пустым.")
        return value