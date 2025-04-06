from django.db import models
from django.contrib.auth.models import User

class Stock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stocks')
    is_pinned = models.BooleanField(default=False)
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    shares = models.PositiveIntegerField(default=0)
    sector = models.CharField(max_length=100, blank=True)
    avgPrice = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.symbol} - {self.name}"

class Alert(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='alerts')
    symbol = models.CharField(max_length=10)
    type = models.CharField(max_length=50)
    message = models.TextField()
    severity = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    triggerPrice = models.DecimalField(max_digits=12, decimal_places=2)
    triggered = models.BooleanField(default=False) 

    def __str__(self):
        return f"Alert for {self.symbol} ({self.type})"

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists')
    name = models.CharField(max_length=100)
    stocks = models.ManyToManyField(Stock, blank=True, related_name='watchlists')

    def __str__(self):
        return self.name
