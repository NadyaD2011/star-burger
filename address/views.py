from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist

from decimal import Decimal, InvalidOperation
from address.models import Place
import requests


def fetch_coordinates(apikey, address):
    try:
        address_obj = Place.objects.get(address=address)
        lon = address_obj.lon
        lat = address_obj.lat
        if lon is None or lat is None:
            raise ObjectDoesNotExist
        return float(lat), float(lon)

    except ObjectDoesNotExist:
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
                return None

            most_relevant = found_places[0]
            pos = most_relevant['GeoObject']['Point']['pos'].split(" ")
            lon_str, lat_str = pos[0], pos[1]

            try:
                lon = Decimal(lon_str.strip())
                lat = Decimal(lat_str.strip())
            except InvalidOperation:
                return None

            Place.objects.filter(address=address).delete()
            Place.objects.create(address=address, lon=lon, lat=lat)

            return float(lat), float(lon)

        except (requests.HTTPError, requests.RequestException, KeyError, ValueError, TypeError):
            return None

