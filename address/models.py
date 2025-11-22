from django.db import models


class Address(models.Model):
    name = models.CharField(
        'название адреса',
        max_length=250
    )
    lon = models.DecimalField(
        'долгота',
        max_digits=5,
        decimal_places=2,
    )
    lat = models.DecimalField(
        'широта',
        max_digits=5,
        decimal_places=2,
    )

    class Meta:
        verbose_name = 'адрес'
        verbose_name_plural = 'адреса'
        unique_together = [
            ['name', 'lon', 'lat']
        ]

    def __str__(self):
        return f"{self.name} ({self.lat}, {self.lon})"
