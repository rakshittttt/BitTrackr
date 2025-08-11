import requests
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import time
import json
import schedule
from typing import List, Dict, Optional
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

class CryptoPriceTracker:
    def __init__(self, db_path: str = "crypto_prices.db"):
        self.db_path = db_path
        self.api_key = os.getenv("COINGECKO_API_KEY")
        # Optional: explicitly set API tier ("pro" or "free"). If not set, infer from base URL
        self.api_tier = os.getenv("COINGECKO_API_TIER", "").strip().lower()
        env_base_url = os.getenv("COINGECKO_API_BASE_URL")
        if env_base_url:
            self.base_url = env_base_url
        else:
            # Default to free endpoint; we will upgrade automatically if api_tier=="pro"
            self.base_url = "https://api.coingecko.com/api/v3"
            if self.api_tier == "pro":
                self.base_url = "https://pro-api.coingecko.com/api/v3"
        self.setup_database()
        
    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                price_usd REAL NOT NULL,
                market_cap REAL,
                volume_24h REAL,
                percent_change_24h REAL,
                percent_change_7d REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                rank_position INTEGER
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
            ON price_data(symbol, timestamp)
        """)
        
        conn.commit()
        conn.close()
        
    def _build_headers(self, use_pro_header: bool) -> Dict[str, str]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        if self.api_key:
            if use_pro_header:
                headers['x-cg-pro-api-key'] = self.api_key
            else:
                headers['x-cg-demo-api-key'] = self.api_key
        return headers
        
    def fetch_crypto_data(self, limit: int = 50) -> Optional[List[Dict]]:
        """
        Fetch cryptocurrency data from CoinGecko API.
        
        Args:
            limit: Number of cryptocurrencies to fetch (max 250)
            
        Returns:
            List of cryptocurrency data dictionaries
        """
        url_path = "/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            # Send string to avoid servers interpreting Python bools
            'sparkline': 'false',
            'price_change_percentage': '24h,7d'
        }
        
        # Determine whether to try pro first
        should_try_pro = (
            self.api_tier == 'pro' or 'pro-api' in (self.base_url or '')
        )
        
        try_order = []
        if should_try_pro:
            try_order.append({
                'base_url': 'https://pro-api.coingecko.com/api/v3',
                'use_pro_header': True
            })
        # Always include free endpoint as fallback or primary
        try_order.append({
            'base_url': 'https://api.coingecko.com/api/v3',
            'use_pro_header': False
        })
        
        last_error: Optional[Exception] = None
        for attempt in try_order:
            url = f"{attempt['base_url']}{url_path}"
            headers = self._build_headers(use_pro_header=attempt['use_pro_header'])
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
                if response.status_code >= 400:
                    # Try to surface helpful error info
                    try:
                        err_json = response.json()
                        print(f"API error {response.status_code} at {url}: {err_json}")
                    except Exception:
                        print(f"API error {response.status_code} at {url}: {response.text[:300]}")
                    response.raise_for_status()
                data = response.json()
                print(f"Successfully fetched data for {len(data)} cryptocurrencies from {'PRO' if attempt['use_pro_header'] else 'FREE'} endpoint")
                # Update base_url to the successful one
                self.base_url = attempt['base_url']
                return data
            except requests.exceptions.RequestException as e:
                last_error = e
                # Proceed to next attempt in fallback order
                continue
            except json.JSONDecodeError as e:
                last_error = e
                continue
        
        if last_error:
            print(f"Error fetching data after trying {len(try_order)} endpoint(s): {last_error}")
        return None
            
    def store_data(self, crypto_data: List[Dict]):
        if not crypto_data:
            print("No data to store")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for crypto in crypto_data:
            try:
                cursor.execute("""
                    INSERT INTO price_data (
                        symbol, name, price_usd, market_cap, volume_24h,
                        percent_change_24h, percent_change_7d, rank_position
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    crypto.get('symbol', '').upper(),
                    crypto.get('name', ''),
                    crypto.get('current_price', 0),
                    crypto.get('market_cap', 0),
                    crypto.get('total_volume', 0),
                    crypto.get('price_change_percentage_24h', 0),
                    crypto.get('price_change_percentage_7d', 0),
                    crypto.get('market_cap_rank', 0)
                ))
            except Exception as e:
                print(f"Error storing data for {crypto.get('name', 'Unknown')}: {e}")
                
        conn.commit()
        conn.close()
        print(f"Stored data for {len(crypto_data)} cryptocurrencies")
        
    def get_price_history(self, symbol: str, days: int = 14) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT * FROM price_data 
            WHERE symbol = ? AND timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp
        """.format(days)
        
        df = pd.read_sql_query(query, conn, params=(symbol.upper(),))
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        return df
        
    def get_all_data(self, days: int = 14) -> pd.DataFrame:
        """Get all cryptocurrency data from the last N days."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT * FROM price_data 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp, rank_position
        """.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        return df
        
    def visualize_price_trends(self, symbols: List[str], days: int = 14):
        plt.figure(figsize=(15, 10))
        
        for i, symbol in enumerate(symbols, 1):
            df = self.get_price_history(symbol, days)
            
            if df.empty:
                print(f"No data found for {symbol}")
                continue
                
            plt.subplot(2, 2, i if i <= 4 else 4)
            plt.plot(df['timestamp'], df['price_usd'], marker='o', linewidth=2)
            plt.title(f'{symbol} Price Trend ({days} days)', fontsize=12, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Price (USD)')
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            if len(df) > 1:
                price_change = ((df['price_usd'].iloc[-1] / df['price_usd'].iloc[0]) - 1) * 100
                color = 'green' if price_change > 0 else 'red'
                plt.text(0.02, 0.95, f'{price_change:.1f}%', 
                        transform=plt.gca().transAxes, 
                        color=color, fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        plt.show()
        
    def analyze_volatility(self, days: int = 14):
        df = self.get_all_data(days)
        
        if df.empty:
            print("No data available for volatility analysis")
            return
        volatility_data = []
        
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].sort_values('timestamp')
            
            if len(symbol_data) > 1:
                prices = symbol_data['price_usd'].values
                returns = np.diff(np.log(prices))
                volatility = np.std(returns) * np.sqrt(len(returns))
                
                volatility_data.append({
                    'symbol': symbol,
                    'name': symbol_data['name'].iloc[0],
                    'volatility': volatility,
                    'avg_price': np.mean(prices),
                    'price_range': np.max(prices) - np.min(prices)
                })
        
        volatility_df = pd.DataFrame(volatility_data)
        volatility_df = volatility_df.sort_values('volatility', ascending=False)
        plt.figure(figsize=(15, 8))
        top_volatile = volatility_df.head(10)
        
        plt.subplot(1, 2, 1)
        plt.barh(range(len(top_volatile)), top_volatile['volatility'])
        plt.yticks(range(len(top_volatile)), top_volatile['symbol'])
        plt.title('Top 10 Most Volatile Cryptocurrencies', fontweight='bold')
        plt.xlabel('Volatility')
        plt.subplot(1, 2, 2)
        plt.scatter(volatility_df['avg_price'], volatility_df['volatility'], alpha=0.6)
        plt.xlabel('Average Price (USD)')
        plt.ylabel('Volatility')
        plt.title('Price vs Volatility Relationship', fontweight='bold')
        plt.xscale('log')
        for i, row in volatility_df.head(5).iterrows():
            plt.annotate(row['symbol'], 
                        (row['avg_price'], row['volatility']),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=8, alpha=0.7)
        
        plt.tight_layout()
        plt.show()
        
        return volatility_df
        
    def get_gainers_losers(self, days: int = 1) -> Dict:
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT symbol, name, price_usd, percent_change_24h, percent_change_7d, market_cap
            FROM price_data p1
            WHERE timestamp = (
                SELECT MAX(timestamp) 
                FROM price_data p2 
                WHERE p2.symbol = p1.symbol
            )
            AND percent_change_24h IS NOT NULL
            ORDER BY percent_change_24h DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return {'gainers': [], 'losers': []}
        gainers = df.head(10).to_dict('records')
        losers = df.tail(10).to_dict('records')
        losers.reverse()
        
        return {'gainers': gainers, 'losers': losers}
        
    def visualize_gainers_losers(self):
        data = self.get_gainers_losers()
        
        if not data['gainers'] and not data['losers']:
            print("No data available for gainers/losers analysis")
            return
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        if data['gainers']:
            gainers_df = pd.DataFrame(data['gainers'])
            ax1.barh(range(len(gainers_df)), gainers_df['percent_change_24h'], color='green', alpha=0.7)
            ax1.set_yticks(range(len(gainers_df)))
            ax1.set_yticklabels(gainers_df['symbol'])
            ax1.set_title('Top 10 Gainers (24h)', fontweight='bold', color='green')
            ax1.set_xlabel('Price Change (%)')
            for i, v in enumerate(gainers_df['percent_change_24h']):
                ax1.text(v + 0.5, i, f'{v:.1f}%', va='center')
        if data['losers']:
            losers_df = pd.DataFrame(data['losers'])
            ax2.barh(range(len(losers_df)), losers_df['percent_change_24h'], color='red', alpha=0.7)
            ax2.set_yticks(range(len(losers_df)))
            ax2.set_yticklabels(losers_df['symbol'])
            ax2.set_title('Top 10 Losers (24h)', fontweight='bold', color='red')
            ax2.set_xlabel('Price Change (%)')
            for i, v in enumerate(losers_df['percent_change_24h']):
                ax2.text(v - 0.5, i, f'{v:.1f}%', va='center', ha='right')
        
        plt.tight_layout()
        plt.show()
        
    def market_cap_analysis(self):
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT symbol, name, market_cap, rank_position
            FROM price_data p1
            WHERE timestamp = (
                SELECT MAX(timestamp) 
                FROM price_data p2 
                WHERE p2.symbol = p1.symbol
            )
            AND market_cap > 0
            ORDER BY market_cap DESC
            LIMIT 20
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("No market cap data available")
            return
        plt.figure(figsize=(15, 10))
        plt.subplot(2, 2, 1)
        top_10 = df.head(10)
        others_cap = df[10:]['market_cap'].sum() if len(df) > 10 else 0
        
        sizes = list(top_10['market_cap']) + ([others_cap] if others_cap > 0 else [])
        labels = list(top_10['symbol']) + (['Others'] if others_cap > 0 else [])
        
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title('Market Cap Distribution (Top 10)', fontweight='bold')
        plt.subplot(2, 2, 2)
        plt.bar(range(len(top_10)), top_10['market_cap'] / 1e9)
        plt.xticks(range(len(top_10)), top_10['symbol'], rotation=45)
        plt.title('Market Cap (Billions USD)', fontweight='bold')
        plt.ylabel('Market Cap (Billions)')
        plt.subplot(2, 1, 2)
        plt.scatter(df['rank_position'], df['market_cap'] / 1e9, alpha=0.6, s=100)
        plt.xlabel('Market Cap Rank')
        plt.ylabel('Market Cap (Billions USD)')
        plt.title('Market Cap vs Ranking', fontweight='bold')
        plt.yscale('log')
        for i, row in df.head(5).iterrows():
            plt.annotate(row['symbol'], 
                        (row['rank_position'], row['market_cap'] / 1e9),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=8, alpha=0.7)
        
        plt.tight_layout()
        plt.show()
        
    def daily_data_collection(self):
        """Collect data once - to be called by scheduler."""
        print(f"Starting data collection at {datetime.now()}")
        crypto_data = self.fetch_crypto_data(limit=100)  
        
        if crypto_data:
            self.store_data(crypto_data)
            print("Data collection completed successfully")
        else:
            print("Data collection failed")
            
    def setup_daily_schedule(self):
        schedule.every().day.at("09:00").do(self.daily_data_collection)
        print("Daily data collection scheduled for 9:00 AM")
        
    def run_scheduler(self):
        """Run the scheduled data collection."""
        print("Starting cryptocurrency price tracker scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    def generate_report(self, days: int = 7):
        """Generate a comprehensive analysis report."""
        print(f"\n{'='*60}")
        print(f"CRYPTOCURRENCY MARKET REPORT - LAST {days} DAYS")
        print(f"{'='*60}")
        gainers_losers = self.get_gainers_losers()
        
        if gainers_losers['gainers']:
            print(f"\nTOP 5 GAINERS (24h):")
            print("-" * 40)
            for i, crypto in enumerate(gainers_losers['gainers'][:5], 1):
                print(f"{i}. {crypto['symbol']} ({crypto['name']}): +{crypto['percent_change_24h']:.2f}%")
                
        if gainers_losers['losers']:
            print(f"\nTOP 5 LOSERS (24h):")
            print("-" * 40)
            for i, crypto in enumerate(gainers_losers['losers'][:5], 1):
                print(f"{i}. {crypto['symbol']} ({crypto['name']}): {crypto['percent_change_24h']:.2f}%")
        
        
        print(f"\nVOLATILITY ANALYSIS:")
        print("-" * 40)
        volatility_df = self.analyze_volatility(days)
        if not volatility_df.empty:
            print("Most volatile cryptocurrencies:")
            for i, row in volatility_df.head(3).iterrows():
                print(f"- {row['symbol']}: {row['volatility']:.4f}")
        
        print(f"\n{'='*60}")
if __name__ == "__main__":
    tracker = CryptoPriceTracker()
    print("Collecting initial cryptocurrency data...")
    crypto_data = tracker.fetch_crypto_data(limit=50)
    if crypto_data:
        tracker.store_data(crypto_data)
    print("Waiting 5 seconds before collecting another batch...")
    time.sleep(5)
    crypto_data = tracker.fetch_crypto_data(limit=50)
    if crypto_data:
        tracker.store_data(crypto_data)
    print("\nGenerating visualizations...")
    major_cryptos = ['BTC', 'ETH', 'BNB', 'XRP']
    tracker.visualize_price_trends(major_cryptos, days=1)
    tracker.analyze_volatility(days=1)
    tracker.visualize_gainers_losers()
    tracker.market_cap_analysis()
    tracker.generate_report(days=1)
    print("\nCryptocurrency Price Tracker setup complete!")
    print("To run daily data collection, call: tracker.setup_daily_schedule() and tracker.run_scheduler()")