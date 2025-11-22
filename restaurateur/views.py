from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, F, Count
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant, Order
from address.models import Address
from star_burger.settings import YANDEX_API_KEY

from decimal import Decimal, InvalidOperation
from geopy import distance
import requests


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


def get_restaurants_for_order_efficient(order):
    order_items = order.order_items.all()

    if not order_items.exists():
        return Restaurant.objects.none()

    product_ids = list(order_items.values_list('product_id', flat=True))

    restaurants = Restaurant.objects.filter(
        menu_items__product__in=product_ids,
        menu_items__availability=True,
    ).annotate(
        available_items_count=Count('menu_items__product', distinct=True)
    ).filter(
        available_items_count=len(set(product_ids))
    ).distinct()

    return restaurants


def fetch_coordinates(apikey, address):
    try:
        try:
            address = Address.objects.get(name=address)
            lon = address.lon
            lat = address.lat
            if lon is None or lat is None:
                raise ObjectDoesNotExist
        except ObjectDoesNotExist:
            base_url = "https://geocode-maps.yandex.ru/1.x"
            response = requests.get(base_url, params={
                "geocode": address,
                "apikey": apikey,
                "format": "json",
            })
            response.raise_for_status()
            found_places = response.json()['response']['GeoObjectCollection']['featureMember']

            if not found_places:
                return None

            most_relevant = found_places[0]
            lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")

            try:
                lon = Decimal(lon.strip())
                lat = Decimal(lat.strip())
            except InvalidOperation:
                return None

            Address.objects.filter(name=address).delete()
            Address.objects.create(
                name=address,
                lon=lon,
                lat=lat
            )
        return float(lat), float(lon)
    except (requests.HTTPError, requests.RequestException, KeyError, ValueError, TypeError):
        return None


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    apikey = YANDEX_API_KEY

    orders = Order.objects.filter(status__in=["pending", "processing"]).annotate(
        priсe=Sum(F('order_items__price') * F('order_items__quantity'))
    )

    for order in orders:
        restaurants = get_restaurants_for_order_efficient(order)
        ready_restaurants = []

        for restaurant in restaurants:
            address_restaurant = fetch_coordinates(apikey, Restaurant.objects.filter(name=restaurant).first().address)
            if address_restaurant is None:
                continue

            address_order = fetch_coordinates(apikey, order.address)
            if address_order is None:
                continue

            distance_order = distance.distance(
                address_restaurant,
                address_order
            ).km

            ready_restaurants.append({
                'name': restaurant,
                'distance': round(distance_order, 2)
            })

        order.ready_restaurants = sorted(ready_restaurants, key=lambda x: x['distance'])

    return render(request, template_name='order_items.html',
                  context={'order_items': orders})
