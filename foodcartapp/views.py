from django.http import JsonResponse
from django.templatetags.static import static

from .models import Product, Order, OrderItem

import json


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def register_order(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        print(data)
        order = Order.objects.create(
            name=data['firstname'],
            surname =data['lastname'],
            phone_number=data['phonenumber'],
            address=data['address']
        )
        for item in data['products']:
            product_id = item['product']
            quantity = item['quantity']

            product = Product.objects.get(id=product_id)
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity
            )

        return JsonResponse(
            {
                'status': "ok",
                'message': 'Данные получены',
                'order_id': order.id
            }
        )
    except ValueError:
        return JsonResponse({
            'status': 'error: ValueError',
        })
