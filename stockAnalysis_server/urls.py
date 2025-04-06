from django.urls import path, include

urlpatterns = [
    path('auth/', include('authapp.urls')),
    path('', include('stocks.urls')),
]
