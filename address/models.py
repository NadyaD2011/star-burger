from django.db import models


class Place(models.Model):
    address = models.CharField(
        'название адреса',
        max_length=250
    )
    lon = models.DecimalField(
        'долгота',
        max_digits=5,
        decimal_places=2,
        null=True
    )
    lat = models.DecimalField(
        'широта',
        max_digits=5,
        decimal_places=2,
        null=True
    )

    class Meta:
        verbose_name = 'адрес'
        verbose_name_plural = 'адреса'
        unique_together = [
            ['address']
        ]

    def __str__(self):
        return f"{self.address} ({self.lat}, {self.lon})"
    
    @property
    def coordinates(self):
        if self.lat is not None and self.lon is not None:
            return (self.lat, self.lon)
        return None
