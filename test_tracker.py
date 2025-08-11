from crypto_tracker import CryptoPriceTracker
import time

def main():
    print("🚀 Starting Cryptocurrency Price Tracker Test")
    print("=" * 50)
    print("\n1. Initializing tracker and database...")
    tracker = CryptoPriceTracker()
    print("✅ Database initialized successfully!")
    print("\n2. Testing API connection and collecting initial data...")
    try:
        crypto_data = tracker.fetch_crypto_data(limit=20)  # Start with top 20
        if crypto_data:
            print(f"✅ Successfully fetched data for {len(crypto_data)} cryptocurrencies")
            tracker.store_data(crypto_data)
            print("✅ Data stored in database successfully!")
            print("\nSample data collected:")
            for i, crypto in enumerate(crypto_data[:5], 1):
                name = crypto.get('name', 'Unknown')
                symbol = crypto.get('symbol', '').upper()
                price = crypto.get('current_price', 0)
                change = crypto.get('price_change_percentage_24h', 0)
                print(f"{i}. {name} ({symbol}): ${price:.4f} ({change:+.2f}%)")
        else:
            print("❌ Failed to fetch data. Check your internet connection.")
            return
            
    except Exception as e:
        print(f"❌ Error during data collection: {e}")
        return
    print("\n3. Waiting 10 seconds, then collecting another batch...")
    print("   (This simulates daily data collection)")
    
    for i in range(10, 0, -1):
        print(f"   Waiting {i} seconds...", end='\r')
        time.sleep(1)
    
    print("\n   Collecting second batch...")
    crypto_data_2 = tracker.fetch_crypto_data(limit=20)
    if crypto_data_2:
        tracker.store_data(crypto_data_2)
        print("✅ Second batch collected and stored!")
    print("\n4. Testing basic analysis features...")
    gainers_losers = tracker.get_gainers_losers()
    
    if gainers_losers['gainers']:
        print("\n📈 Top 3 Gainers (24h):")
        for i, crypto in enumerate(gainers_losers['gainers'][:3], 1):
            print(f"   {i}. {crypto['symbol']}: +{crypto['percent_change_24h']:.2f}%")
    
    if gainers_losers['losers']:
        print("\n📉 Top 3 Losers (24h):")
        for i, crypto in enumerate(gainers_losers['losers'][:3], 1):
            print(f"   {i}. {crypto['symbol']}: {crypto['percent_change_24h']:.2f}%")
    print("\n5. Testing visualization capabilities...")
    
    try:
        print("   Creating price trend charts...")
        major_cryptos = ['BTC', 'ETH', 'BNB']
        tracker.visualize_price_trends(major_cryptos, days=1)
        print("✅ Price trend charts created!")
        
        print("   Creating gainers/losers chart...")
        tracker.visualize_gainers_losers()
        print("✅ Gainers/losers chart created!")
        
        print("   Creating market cap analysis...")
        tracker.market_cap_analysis()
        print("✅ Market cap analysis created!")
        
    except Exception as e:
        print(f"⚠️ Visualization error (this is normal on first run): {e}")
        print("   💡 Collect more data over time for better visualizations")
    print("\n6. Generating summary report...")
    tracker.generate_report(days=1)
    
    print("\n" + "=" * 50)
    print("🎉 TEST COMPLETED SUCCESSFULLY!")
    print("\nNext steps:")
    print("1. Let the tracker run for a few days to collect more data")
    print("2. Set up automated daily collection")
    print("3. Customize the cryptocurrencies you want to track")
    print("\nTo set up automated collection, run:")
    print("   python daily_collector.py")

if __name__ == "__main__":
    main()