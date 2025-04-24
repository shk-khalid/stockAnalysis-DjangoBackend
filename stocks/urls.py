from django.urls import path, re_path
from . import consumers
from .views import (
    StockSearchView,
    WatchlistListCreateView,
    WatchlistDestroyView,
    AddStockToWatchlistView,
    RemoveStockFromWatchlistView,
    WatchlistOverviewView,
    WatchlistDetailOverviewView,
    TogglePinStockView,
    AlertCreateView,
    AlertDeleteView,
    
)

# HTTP URL patterns
urlpatterns = [
    path('stocks/search/', StockSearchView.as_view(), name='stock-search'),
    path('watchlists/add/', WatchlistListCreateView.as_view(), name='watchlist-list-create'),
    path('watchlists/<int:watchlist_id>/destroy/' , WatchlistDestroyView.as_view(), name='destroy-watchlist'),
    path('watchlists/<int:watchlist_id>/add-stock/', AddStockToWatchlistView.as_view(), name='add-stock-watchlist'),
    path('watchlists/<int:watchlist_id>/remove-stock/<int:stock_id>/', RemoveStockFromWatchlistView.as_view(), name='remove-stock-watchlist'),
    path('watchlist/overview/', WatchlistOverviewView.as_view(), name='watchlist-overview'),
    path('watchlists/<int:watchlist_id>/overview/', WatchlistDetailOverviewView.as_view(), name='watchlist-detail-overview'),
    path('watchlists/<int:watchlist_id>/stocks/<int:stock_id>/toggle-pin/', TogglePinStockView.as_view(), name='toggle-pin-stock'),
    path('alerts/<int:stock_id>/add/', AlertCreateView.as_view(), name='add-alert'),
    path('alerts/<int:alert_id>/delete/', AlertDeleteView.as_view(), name='delete-alert'),
    

]

# WebSocket URL patterns
websocket_urlpatterns = [
    re_path(r'ws/alerts/$', consumers.AlertConsumer.as_asgi()),
]
