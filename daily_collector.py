from crypto_tracker import CryptoPriceTracker
import schedule
import time
from datetime import datetime

def collect_crypto_data():
    """Function to collect cryptocurrency data"""
    print(f"\n🚀 Starting data collection at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    """a comment"""
    try:
        tracker = CryptoPriceTracker()
        crypto_data = tracker.fetch_crypto_data(limit=100)
        
        if crypto_data:
            tracker.store_data(crypto_data)
            print(f"✅ Successfully collected and stored data for {len(crypto_data)} cryptocurrencies")
            btc_data = next((crypto for crypto in crypto_data if crypto.get('symbol', '').upper() == 'BTC'), None)
            eth_data = next((crypto for crypto in crypto_data if crypto.get('symbol', '').upper() == 'ETH'), None)
            if btc_data:
                print(f"   📊 BTC: ${btc_data.get('current_price', 0):,.2f} ({btc_data.get('price_change_percentage_24h', 0):+.2f}%)")
            if eth_data:
                print(f"   📊 ETH: ${eth_data.get('current_price', 0):,.2f} ({eth_data.get('price_change_percentage_24h', 0):+.2f}%)")
        else:
            print("❌ Failed to collect data")
            
    except Exception as e:
        print(f"❌ Error during data collection: {e}")
    
    print(f"✅ Data collection completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    print("🔄 Cryptocurrency Daily Data Collector")
    print("="*50)
    print("📥 Collecting initial data...")
    collect_crypto_data()
    schedule.every().day.at("09:00").do(collect_crypto_data)
    schedule.every().day.at("15:00").do(collect_crypto_data)
    schedule.every().day.at("21:00").do(collect_crypto_data)
    print("\n⏰ Scheduled data collection times:")
    print("   - 9:00 AM daily")
    print("   - 3:00 PM daily") 
    print("   - 9:00 PM daily")
    print("\n🔄 Scheduler is now running... (Press Ctrl+C to stop)")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n\n👋 Scheduler stopped by user")
        print("Data collection has been stopped.")
if __name__ == "__main__":
    main()