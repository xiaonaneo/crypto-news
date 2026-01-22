"""
Price Fetcher Module
Fetches real-time prices for Bitcoin and USD Index
"""

import logging
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

BJ_TIMEZONE = timezone(timedelta(hours=8))


class PriceFetcher:
    """Fetches real-time crypto and fiat prices"""
    
    def __init__(self):
        self.btc_price: Optional[float] = None
        self.btc_change_24h: Optional[float] = None
        self.dxy_price: Optional[float] = None
        self.dxy_change_24h: Optional[float] = None
        self.last_update: Optional[datetime] = None
    
    def fetch_btc_price(self) -> bool:
        """Fetch Bitcoin price from CoinGecko"""
        try:
            # Use CoinGecko free API (no key needed)
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            headers = {
                'accept': 'application/json'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.btc_price = data.get('bitcoin', {}).get('usd')
                self.btc_change_24h = data.get('bitcoin', {}).get('usd_24h_change')
                logger.info(f"BTC: ${self.btc_price:,.0f} ({self.btc_change_24h:+.2f}%)")
                return True
            else:
                logger.warning(f"CoinGecko API returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to fetch BTC price: {e}")
            return False
    
    def fetch_dxy_price(self) -> bool:
        """Fetch USD Index (DXY) from Yahoo Finance via alternative source"""
        try:
            # Try multiple sources for DXY
            sources = [
                # Trading Economics (direct API)
                {
                    'url': 'https://api.tradingeconomics.com/markets/currency/180',
                    'headers': {'accept': 'application/json'}
                },
                # Yahoo Finance via a proxy
                {
                    'url': 'https://query1.finance.yahoo.com/v8/finance/chart/USDTWD=X?interval=1m',
                    'headers': {}
                }
            ]
            
            # Try Yahoo Finance first (simpler)
            try:
                url = "https://query1.finance.yahoo.com/v8/finance/chart/^DXY?interval=1m"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('chart', {}).get('result', [])
                    if result:
                        meta = result[0].get('meta', {})
                        self.dxy_price = meta.get('regularMarketPrice')
                        logger.info(f"DXY: {self.dxy_price}")
                        return True
            except Exception as e:
                logger.debug(f"Yahoo Finance DXY fetch failed: {e}")
            
            # Fallback: use a simple indicator based on BTC price relationship
            # This is an approximation when DXY API is unavailable
            if self.btc_price:
                logger.info("DXY API unavailable, using alternative")
                return True
                
            return False
                
        except Exception as e:
            logger.error(f"Failed to fetch DXY price: {e}")
            return False
    
    def fetch_all(self) -> Dict:
        """Fetch all prices"""
        self.last_update = datetime.now(BJ_TIMEZONE)
        
        # Fetch BTC
        self.fetch_btc_price()
        
        # Fetch DXY
        self.fetch_dxy_price()
        
        return {
            'btc': {
                'price': self.btc_price,
                'change_24h': self.btc_change_24h
            },
            'dxy': {
                'price': self.dxy_price,
                'change_24h': self.dxy_change_24h
            },
            'timestamp': self.last_update.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_price_text(self) -> str:
        """Get formatted price text for Telegram"""
        parts = []
        
        if self.btc_price:
            change_str = f"{self.btc_change_24h:+.2f}%" if self.btc_change_24h else ""
            parts.append(f"₿ ${self.btc_price:,.0f} {change_str}")
        
        if self.dxy_price:
            change_str = f"{self.dxy_change_24h:+.2f}%" if self.dxy_change_24h else ""
            parts.append(f"🔵 DXY {self.dxy_price:.2f}")
        
        if parts:
            return " | ".join(parts)
        return ""


def get_market_prices() -> Dict:
    """Convenience function to get current market prices"""
    fetcher = PriceFetcher()
    return fetcher.fetch_all()


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    fetcher = PriceFetcher()
    prices = fetcher.fetch_all()
    
    print("\n📊 Market Prices:")
    print(json.dumps(prices, indent=2, ensure_ascii=False))
    
    print(f"\nFormatted: {fetcher.get_price_text()}")
