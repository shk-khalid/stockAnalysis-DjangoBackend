import yfinance as yf
from datetime import datetime
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Stock, Watchlist, Alert
from .serializers import StockSerializer, WatchlistSerializer, AlertSerializer


# ----- 1. Stock Search using yfinance -----
class StockSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        query = request.GET.get("query")
        if not query:
            print("Error: Query parameter is required.")
            return Response(
                {"error": "Query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticker = yf.Ticker(query.upper())
        try:
            info = ticker.info
            print(f"Ticker info for {query.upper()}: {info}")
        except Exception as e:
            print(f"Error fetching data for {query}: {str(e)}")
            return Response(
                {"error": f"Error fetching data for {query}: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        price = info.get("regularMarketPrice")
        if price is None:
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist["Close"].iloc[-1]

        if price is None:
            print("Could not retrieve price for this ticker.")
            return Response(
                {"error": "Could not retrieve price for this ticker."},
                status=status.HTTP_404_NOT_FOUND
            )

        search_result = {
            "symbol": info.get("symbol", query.upper()),
            "name": info.get("longName", query.upper()),
            "price": price,
            "change": info.get("regularMarketChange", 0.0),
            "volume": info.get("regularMarketVolume", 0),
            "marketCap": info.get("marketCap", "N/A")
        }
        print(f"Search result: {search_result}")
        return Response(search_result, status=status.HTTP_200_OK)


# ----- 2. Watchlist Endpoints -----

# List and create watchlists for the authenticated user.
class WatchlistListCreateView(generics.ListCreateAPIView):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Watchlist.objects.filter(user=self.request.user)
        print(f"Retrieved watchlists for user {self.request.user}: {list(qs)}")
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        print(f"Created watchlist: {serializer.data}")


# Destroy a specific watchlist.
class WatchlistDestroyView(generics.DestroyAPIView):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'watchlist_id'

    def get_queryset(self):
        qs = Watchlist.objects.filter(user=self.request.user)
        print(f"Watchlist queryset for user {self.request.user}: {list(qs)}")
        return qs


# Add a stock to a specific watchlist.
class AddStockToWatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, watchlist_id, *args, **kwargs):
        symbol = request.data.get("symbol")
        new_shares = request.data.get("shares")
        purchase_price = request.data.get("purchasePrice")

        print(f"Received request to add stock: symbol={symbol}, shares={new_shares}, purchasePrice={purchase_price}")

        if not symbol:
            print("Error: Stock symbol is required.")
            return Response(
                {"error": "Stock symbol is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if new_shares is None or purchase_price is None:
            print("Error: Both 'shares' and 'purchasePrice' are required.")
            return Response(
                {"error": "Both 'shares' and 'purchasePrice' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_shares = int(new_shares)
            purchase_price = float(purchase_price)
        except ValueError:
            print("Error: Invalid data for shares or purchasePrice.")
            return Response(
                {"error": "Invalid data for shares or purchasePrice."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            watchlist = Watchlist.objects.get(id=watchlist_id, user=request.user)
            print(f"Found watchlist: {watchlist.name}")
        except Watchlist.DoesNotExist:
            print("Error: Watchlist not found.")
            return Response(
                {"error": "Watchlist not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        ticker = yf.Ticker(symbol.upper())
        try:
            info = ticker.info
            print(f"Fetched ticker info for {symbol.upper()}: {info}")
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            return Response(
                {"error": f"Error fetching data for {symbol}: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if info.get("regularMarketPrice") is None:
            print(f"Error: Could not retrieve price for {symbol}.")
            return Response(
                {"error": f"Could not retrieve price for {symbol}."},
                status=status.HTTP_404_NOT_FOUND
            )

        name = info.get("longName", symbol.upper())
        sector = info.get("sector", "Unknown")
        print(f"Using name: {name} and sector: {sector}")

        stock_data = {
            "symbol": symbol.upper(),
            "name": name,
            "shares": new_shares,
            "avgPrice": purchase_price,
            "sector": sector,
        }

        try:
            stock = Stock.objects.get(user=request.user, symbol=stock_data["symbol"])
            print(f"Stock already exists. Current shares: {stock.shares}, avgPrice: {stock.avgPrice}")
            existing_shares = stock.shares
            existing_avg = float(stock.avgPrice)
            total_shares = existing_shares + new_shares
            new_avg_price = ((existing_shares * existing_avg) + (new_shares * purchase_price)) / total_shares
            stock.shares = total_shares
            stock.avgPrice = new_avg_price
            stock.sector = sector
            stock.save()
            print(f"Updated stock: {StockSerializer(stock).data}")
        except Stock.DoesNotExist:
            stock = Stock.objects.create(user=request.user, **stock_data)
            print(f"Created new stock: {StockSerializer(stock).data}")

        watchlist.stocks.add(stock)
        print(f"Added stock {stock.symbol} to watchlist {watchlist.name}")

        return Response(
            {"message": "Stock added to watchlist.", "stock": StockSerializer(stock).data},
            status=status.HTTP_201_CREATED
        )


# ----- 3. Detailed Overview for a Specific Watchlist -----
class WatchlistDetailOverviewView(APIView):
    """
    Returns an overview of each stock in a specific watchlist.
    For each stock, returns:
      - symbol, name, price, change, alerts, pinned, sector, marketCap,
        shares, avgPrice, and historical data for the last 7 days.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, watchlist_id, *args, **kwargs):
        try:
            watchlist = Watchlist.objects.get(id=watchlist_id, user=request.user)
            print(f"Retrieved watchlist: {watchlist.name}")
        except Watchlist.DoesNotExist:
            print("Error: Watchlist not found.")
            return Response(
                {"error": "Watchlist not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        overview = []
        for stock in watchlist.stocks.all():
            print(f"Processing stock: {stock.symbol}")
            ticker = yf.Ticker(stock.symbol)
            try:
                info = ticker.info
                print(f"Ticker info for {stock.symbol}: {info}")
            except Exception as e:
                print(f"Error fetching info for {stock.symbol}: {str(e)}")
                continue

            current_price = info.get("regularMarketPrice", 0)
            try:
                current_price = float(current_price)
            except (TypeError, ValueError):
                current_price = 0.0

            history = ticker.history(period="7d")
            chart_data = []
            if not history.empty and "Close" in history.columns:
                for date, price in history["Close"].items():
                    chart_data.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "price": round(float(price), 2)
                    })
                print(f"Historical chart data for {stock.symbol}: {chart_data}")
            else:
                print(f"No historical data found for {stock.symbol}.")

            alerts = []
            for alert in stock.alerts.all():
                alerts.append({
                    "symbol": alert.symbol,
                    "type": alert.type,
                    "message": alert.message,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                    "triggerPrice": float(alert.triggerPrice)
                })
            print(f"Alerts for {stock.symbol}: {alerts}")

            stock_overview = {
                "symbol": stock.symbol,
                "name": stock.name,
                "price": current_price,
                "change": info.get("regularMarketChange", 0.0),
                "alerts": alerts,
                "pinned": stock.is_pinned,
                "sector": stock.sector,
                "marketCap": info.get("marketCap", "N/A"),
                "shares": stock.shares,
                "avgPrice": float(stock.avgPrice),
                "chartData": chart_data,
            }
            overview.append(stock_overview)
            print(f"Overview for {stock.symbol}: {stock_overview}")

        return Response(overview, status=status.HTTP_200_OK)


# ----- 4. Overall Watchlist Overview Endpoint -----
class WatchlistOverviewView(APIView):
    """
    Returns an overall overview for all stocks across all watchlists of the user.
    It returns:
      - overallTotalValue: Sum of (currentPrice * shares) for each stock.
      - overallTotalGainLoss: Sum of (currentPrice - avgPrice) * shares.
      - For each stock: last 7 days historical data and upcoming dividend details (if available).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        stocks = Stock.objects.filter(user=request.user)
        overall_total_value = 0.0
        overall_total_gainloss = 0.0
        stocks_overview = []

        for stock in stocks:
            print(f"Processing overall data for stock: {stock.symbol}")
            ticker = yf.Ticker(stock.symbol)
            try:
                info = ticker.info
                print(f"Ticker info for {stock.symbol}: {info}")
            except Exception as e:
                print(f"Error fetching info for {stock.symbol}: {str(e)}")
                continue

            current_price = info.get("regularMarketPrice", 0)
            try:
                current_price = float(current_price)
            except (TypeError, ValueError):
                current_price = 0.0

            total_value = current_price * stock.shares
            gain_loss = (current_price - float(stock.avgPrice)) * stock.shares

            overall_total_value += total_value
            overall_total_gainloss += gain_loss

            history = ticker.history(period="7d")
            hist_data = []
            if not history.empty and "Close" in history.columns:
                for date, price in history["Close"].items():
                    hist_data.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "price": round(float(price), 2)
                    })
                print(f"Historical data for {stock.symbol}: {hist_data}")

            upcoming_dividend = None
            dividend_date = info.get("dividendDate")
            dividend_rate = info.get("dividendRate")
            if dividend_date and dividend_rate:
                try:
                    payment_date = datetime.fromtimestamp(dividend_date).strftime("%Y-%m-%d")
                except Exception:
                    payment_date = None
                dividend_yield = info.get("dividendYield")
                if dividend_yield is None and current_price:
                    dividend_yield = round(dividend_rate / current_price, 4)
                upcoming_dividend = {
                    "paymentDate": payment_date,
                    "amount": float(dividend_rate),
                    "yield": dividend_yield if dividend_yield is not None else 0.0
                }
                print(f"Upcoming dividend for {stock.symbol}: {upcoming_dividend}")

            stocks_overview.append({
                "symbol": stock.symbol,
                "historicalData": hist_data,
                "mostRecentDividend": upcoming_dividend
            })

        overall = {
            "overallTotalValue": overall_total_value,
            "overallTotalGainLoss": overall_total_gainloss,
            "stocks": stocks_overview
        }
        print(f"Overall watchlist overview: {overall}")

        return Response(overall, status=status.HTTP_200_OK)


# ----- 5. Alert Endpoints -----

# Create an alert for a given stock.
class AlertCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, stock_id, *args, **kwargs):
        try:
            stock = Stock.objects.get(id=stock_id, user=request.user)
            print(f"Found stock for alert: {stock.symbol}")
        except Stock.DoesNotExist:
            print("Error: Stock not found for alert creation.")
            return Response(
                {"error": "Stock not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AlertSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(stock=stock)
            print(f"Created alert: {serializer.data}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print(f"Alert creation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Remove an alert.
class AlertDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, alert_id, *args, **kwargs):
        try:
            alert = Alert.objects.get(id=alert_id, stock__user=request.user)
            print(f"Found alert to delete: {alert}")
        except Alert.DoesNotExist:
            print("Error: Alert not found for deletion.")
            return Response(
                {"error": "Alert not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        alert.delete()
        print(f"Deleted alert with id: {alert_id}")
        return Response(
            {"message": "Alert deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


# ----- 6. Remove Stock from Watchlist Endpoint -----
class RemoveStockFromWatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, watchlist_id, stock_id, *args, **kwargs):
        try:
            watchlist = Watchlist.objects.get(id=watchlist_id, user=request.user)
            print(f"Found watchlist for removal: {watchlist.name}")
        except Watchlist.DoesNotExist:
            print("Error: Watchlist not found for removal.")
            return Response(
                {"error": "Watchlist not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            stock = Stock.objects.get(id=stock_id, user=request.user)
            print(f"Found stock for removal: {stock.symbol}")
        except Stock.DoesNotExist:
            print("Error: Stock not found for removal.")
            return Response(
                {"error": "Stock not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if stock not in watchlist.stocks.all():
            print("Error: Stock is not in this watchlist.")
            return Response(
                {"error": "Stock is not in this watchlist."},
                status=status.HTTP_400_BAD_REQUEST
            )

        watchlist.stocks.remove(stock)
        print(f"Removed stock {stock.symbol} from watchlist {watchlist.name}")
        return Response(
            {
                "message": "Stock removed from watchlist successfully.",
                "stock": StockSerializer(stock).data
            },
            status=status.HTTP_200_OK
        )
