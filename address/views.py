from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist

from decimal import Decimal, InvalidOperation
from address.models import Place
import requests


def fetch_coordinates(apikey, address):
    try:
        address_obj = Place.objects.get(address=address)

        if address_obj.lat is not None and address_obj.lon is not None:
            return float(address_obj.lat), float(address_obj.lon)
        return None
    except Place.DoesNotExist:
        pass

    base_url = "https://geocode-maps.yandex.ru/1.x"
    try:
        response = requests.get(
            base_url,
            params={
                "geocode": address,
                "apikey": apikey,
                "format": "json",
            }
        )
        response.raise_for_status()
        data = response.json()
        found_places = data['response']['GeoObjectCollection']['featureMember']

        if not found_places:
            Place.objects.create(address=address, lon=None, lat=None)
            return None

        most_relevant = found_places[0]
        pos = most_relevant['GeoObject']['Point']['pos'].split()
        lon_str, lat_str = pos[0], pos[1]

        try:
            lon = Decimal(lon_str.strip())
            lat = Decimal(lat_str.strip())
        except InvalidOperation:
            Place.objects.create(address=address, lon=None, lat=None)
            return None

        Place.objects.create(address=address, lon=lon, lat=lat)
        return float(lat), float(lon)

    except (requests.RequestException, KeyError, ValueError, TypeError):
        Place.objects.create(address=address, lon=None, lat=None)
        return None
