from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.db import transaction

from foodcartapp.models import Product, Restaurant, Order
from address.models import Place
from star_burger.settings import YANDEX_API_KEY
from address.views import fetch_coordinates
from django.db.models import Count

from geopy import distance


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


def get_or_create_coordinates(addresses, apikey):
    unique_addresses = set(addr.strip() for addr in addresses if addr and addr.strip())
    if not unique_addresses:
        return {}

    existing_places = Place.objects.filter(address__in=unique_addresses)
    coords = {place.address: place.coordinates for place in existing_places}

    missing_addresses = unique_addresses - set(coords.keys())

    new_places = []
    for addr in missing_addresses:
        yandex_coords = fetch_coordinates(apikey, addr)
        if yandex_coords:
            lat, lon = yandex_coords
            new_places.append(Place(address=addr, lat=lat, lon=lon))
            coords[addr] = (lat, lon)
        else:
            coords[addr] = None

    if new_places:
        with transaction.atomic():
            Place.objects.bulk_create(new_places, ignore_conflicts=True)

    return coords


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = (
        Order.objects
        .get_total_price()
        .filter(status__in=["pending", "processing"])
        .annotate_available_restaurants()
    )

    if not orders:
        return render(request, 'order_items.html', {'order_items': []})

    addresses = set()
    restaurant_ids = set()

    for order in orders:
        addresses.add(order.address)
        restaurant_ids.update(order.available_restaurant_ids)

    restaurants_by_id = {}
    if restaurant_ids:
        restaurants = Restaurant.objects.filter(id__in=restaurant_ids)
        for r in restaurants:
            restaurants_by_id[r.id] = r
            addresses.add(r.address)

    coords_map = get_or_create_coordinates(addresses, YANDEX_API_KEY)

    for order in orders:
        ready_restaurants = []
        order_coords = coords_map.get(order.address)

        for rest_id in order.available_restaurant_ids:
            restaurant = restaurants_by_id.get(rest_id)
            if not restaurant:
                continue

            rest_coords = coords_map.get(restaurant.address)

            if order_coords and rest_coords:
                dist_km = distance.distance(order_coords, rest_coords).km
                ready_restaurants.append({
                    'name': restaurant,
                    'distance': round(dist_km, 2)
                })

        order.ready_restaurants = sorted(ready_restaurants, key=lambda x: x['distance'])

    return render(request, 'order_items.html', {'order_items': orders})
