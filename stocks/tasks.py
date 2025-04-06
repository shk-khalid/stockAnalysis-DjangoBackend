import yfinance as yf
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import timezone
from .models import Alert

@shared_task
def check_stock_alerts():
    # Get all alerts that haven't been triggered.
    alerts = Alert.objects.filter(triggered=False)
    for alert in alerts:
        # Use yfinance to fetch the latest price for the stock.
        ticker = yf.Ticker(alert.symbol)
        try:
            info = ticker.info
        except Exception:
            continue  # Skip if we can't get info

        current_price = info.get("regularMarketPrice")
        if current_price is None:
            continue

        try:
            current_price = float(current_price)
        except Exception:
            continue

        # Determine if the alert condition is met.
        condition_met = False
        if alert.type.lower() == "above" and current_price >= float(alert.triggerPrice):
            condition_met = True
        elif alert.type.lower() == "below" and current_price <= float(alert.triggerPrice):
            condition_met = True

        if condition_met:
            alert.triggered = True  
            alert.last_triggered = timezone.now()  # Store last triggered time
            alert.save()

            # Send an email notification.
            subject = f"Alert Triggered for {alert.symbol} - Condition: {alert.type.capitalize()}"
            message = (
                f"Hello {alert.stock.user.first_name or alert.stock.user.username},\n\n"
                f"Your alert for {alert.symbol} has been triggered at {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
                f"**Alert Details:**\n"
                f"  - **Type:** {alert.type.capitalize()} (Trigger Price: {float(alert.triggerPrice):.2f})\n"
                f"  - **Current Price:** {current_price:.2f}\n"
                f"  - **Severity:** {alert.severity}\n\n"
                f"**Additional Message:**\n"
                f"{alert.message}\n\n"
                f"Please log in to your account to view more details and manage your alerts.\n\n"
                f"Thank you,\n"
                f"SStockSense Team"
            )
            recipient_list = [alert.stock.user.email]
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

            # Send a real-time update to the frontend via Django Channels.
            channel_layer = get_channel_layer()
            alert_data = {
                "symbol": alert.symbol,
                "type": alert.type,
                "message": alert.message,
                "severity": alert.severity,
                "timestamp": alert.timestamp.isoformat(),
                "triggerPrice": float(alert.triggerPrice),
                "currentPrice": current_price,
            }
            # Assume you have a group per user named "user_{user_id}"
            async_to_sync(channel_layer.group_send)(
                f"user_{alert.stock.user.id}",
                {
                    "type": "send_alert",
                    "alert": alert_data,
                }
            )