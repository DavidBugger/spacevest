from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import requests
from decouple import config
from .models import CryptoRate, SupportedCrypto
from .serializers import CryptoRateSerializer, SupportedCryptoSerializer, CryptoConversionSerializer, CryptoPurchaseQuoteSerializer

COINGECKO_API_URL = config('COINGECKO_API_URL', default='https://api.coingecko.com/api/v3')

class CryptoRateListView(generics.ListAPIView):
    queryset = CryptoRate.objects.all().order_by('cryptocurrency')
    serializer_class = CryptoRateSerializer
    permission_classes = [AllowAny]

class SupportedCryptoListView(generics.ListAPIView):
    queryset = SupportedCrypto.objects.filter(is_active=True).order_by('name')
    serializer_class = SupportedCryptoSerializer
    permission_classes = [AllowAny]

@api_view(['GET'])
@permission_classes([AllowAny])
def get_crypto_rate(request, symbol):
    try:
        crypto_rate = CryptoRate.objects.get(symbol__iexact=symbol)
        serializer = CryptoRateSerializer(crypto_rate)
        return Response(serializer.data)
    except CryptoRate.DoesNotExist:
        return Response({'error': 'Cryptocurrency not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def convert_crypto(request):
    serializer = CryptoConversionSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        
        try:
            crypto_rate = CryptoRate.objects.get(symbol__iexact=data['cryptocurrency'])
            
            if data['to_currency'] == 'NGN':
                converted_amount = data['amount'] * crypto_rate.current_price_ngn
                result = {
                    'from_crypto': data['cryptocurrency'],
                    'to_currency': 'NGN',
                    'amount': data['amount'],
                    'converted_amount': converted_amount,
                    'exchange_rate': crypto_rate.current_price_ngn
                }
            else:  # USD
                converted_amount = data['amount'] * crypto_rate.current_price_usd
                result = {
                    'from_crypto': data['cryptocurrency'],
                    'to_currency': 'USD',
                    'amount': data['amount'],
                    'converted_amount': converted_amount,
                    'exchange_rate': crypto_rate.current_price_usd
                }
            
            return Response(result)
            
        except CryptoRate.DoesNotExist:
            return Response({'error': 'Cryptocurrency not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def get_purchase_quote(request):
    serializer = CryptoPurchaseQuoteSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        
        try:
            crypto_rate = CryptoRate.objects.get(symbol__iexact=data['cryptocurrency'])
            supported_crypto = SupportedCrypto.objects.get(symbol__iexact=data['cryptocurrency'], is_active=True)
            
            # Calculate crypto amount
            crypto_amount = data['amount_ngn'] / crypto_rate.current_price_ngn
            
            # Calculate fees
            network_fee = supported_crypto.network_fee if data['include_fees'] else 0
            total_amount = data['amount_ngn'] + network_fee
            
            quote = {
                'cryptocurrency': data['cryptocurrency'],
                'amount_ngn': data['amount_ngn'],
                'crypto_amount': crypto_amount,
                'exchange_rate': crypto_rate.current_price_ngn,
                'network_fee': network_fee,
                'total_amount': total_amount,
                'min_purchase': supported_crypto.min_purchase_amount,
                'max_purchase': supported_crypto.max_purchase_amount
            }
            
            return Response(quote)
            
        except CryptoRate.DoesNotExist:
            return Response({'error': 'Cryptocurrency not found'}, status=status.HTTP_404_NOT_FOUND)
        except SupportedCrypto.DoesNotExist:
            return Response({'error': 'Cryptocurrency not supported'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def update_crypto_rates(request):
    # This would typically be called by a scheduled task/cron job
    try:
        # Get supported cryptocurrencies
        supported_symbols = list(SupportedCrypto.objects.filter(is_active=True).values_list('symbol', flat=True))
        
        if not supported_symbols:
            return Response({'error': 'No supported cryptocurrencies found'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert symbols to CoinGecko format (lowercase)
        coin_ids = [symbol.lower() for symbol in supported_symbols]
        
        # Make API call to CoinGecko
        response = requests.get(
            f"{COINGECKO_API_URL}/simple/price",
            params={
                'ids': ','.join(coin_ids),
                'vs_currencies': 'usd,ngn',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            for coin_id, rates in data.items():
                symbol = coin_id.upper()
                
                crypto_rate, created = CryptoRate.objects.update_or_create(
                    symbol=symbol,
                    defaults={
                        'cryptocurrency': symbol,
                        'current_price_usd': rates.get('usd', 0),
                        'current_price_ngn': rates.get('ngn', 0),
                        'market_cap': rates.get('usd_market_cap'),
                        'volume_24h': rates.get('usd_24h_vol'),
                        'price_change_24h': rates.get('usd_24h_change'),
                        'price_change_percentage_24h': rates.get('usd_24h_change'),
                    }
                )
            
            return Response({'message': f'Updated rates for {len(data)} cryptocurrencies'})
        else:
            return Response({'error': 'Failed to fetch rates from CoinGecko'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([])
def admin_update_rate(request):
    """
    Admin endpoint to manually update cryptocurrency exchange rates
    """
    from rest_framework.permissions import IsAuthenticated
    from django.contrib.auth.decorators import user_passes_test
    from django.utils import timezone
    
    # Check if user is authenticated and is admin
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not (request.user.is_superuser or getattr(request.user, 'role', '') == 'admin'):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        cryptocurrency = request.data.get('cryptocurrency', '').lower()
        new_rate_ngn = request.data.get('rate_ngn')
        
        if not cryptocurrency or not new_rate_ngn:
            return Response({'error': 'Cryptocurrency and rate_ngn are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            new_rate_ngn = float(new_rate_ngn)
            if new_rate_ngn <= 0:
                return Response({'error': 'Rate must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid rate format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Map cryptocurrency names to symbols
        crypto_mapping = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH', 
            'tether': 'USDT'
        }
        
        symbol = crypto_mapping.get(cryptocurrency)
        if not symbol:
            return Response({'error': 'Unsupported cryptocurrency'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create the crypto rate record
        crypto_rate, created = CryptoRate.objects.get_or_create(
            symbol=symbol,
            defaults={
                'cryptocurrency': symbol,
                'current_price_ngn': new_rate_ngn,
                'current_price_usd': 1.0,  # Default USD price
                'last_updated': timezone.now()
            }
        )
        
        if not created:
            # Update existing record
            crypto_rate.current_price_ngn = new_rate_ngn
            crypto_rate.last_updated = timezone.now()
            crypto_rate.save()
        
        return Response({
            'message': f'Successfully updated {cryptocurrency} rate to ₦{new_rate_ngn}',
            'cryptocurrency': cryptocurrency,
            'symbol': symbol,
            'new_rate_ngn': new_rate_ngn,
            'updated_at': crypto_rate.last_updated
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([])
def admin_get_rates(request):
    """
    Admin endpoint to get all current cryptocurrency rates
    """
    # Check if user is authenticated and is admin
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not (request.user.is_superuser or getattr(request.user, 'role', '') == 'admin'):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        rates = CryptoRate.objects.all().order_by('cryptocurrency')
        rates_data = []
        
        for rate in rates:
            rates_data.append({
                'cryptocurrency': rate.cryptocurrency,
                'symbol': rate.symbol,
                'current_price_ngn': float(rate.current_price_ngn),
                'current_price_usd': float(rate.current_price_usd),
                'last_updated': rate.last_updated
            })
        
        return Response({
            'rates': rates_data,
            'count': len(rates_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
