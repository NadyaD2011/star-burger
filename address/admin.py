from django.contrib import admin

from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    search_fields = [
        'name'
    ]
    list_display = [
        'name',
        'lon',
        'lat'
    ]
