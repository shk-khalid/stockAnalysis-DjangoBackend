from rest_framework import serializers
from .models import Stock, Watchlist, Alert

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['id', 'symbol', 'name', 'is_pinned', 'shares', 'sector', 'avgPrice']
        read_only_fields = ['id']

class WatchlistSerializer(serializers.ModelSerializer):
    # Nested stock serializer; stocks will be read-only here.
    stocks = StockSerializer(many=True, read_only=True)

    class Meta:
        model = Watchlist
        fields = ['id', 'name', 'stocks']
        read_only_fields = ['id']

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'id', 'symbol', 'type', 'message',
            'severity', 'timestamp', 'triggerPrice'
        ]
        read_only_fields = ['id', 'timestamp']
