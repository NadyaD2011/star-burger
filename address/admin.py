from django.contrib import admin

from .models import Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    search_fields = [
        'address'
    ]
    list_display = [
        'address',
        'lon',
        'lat'
    ]
