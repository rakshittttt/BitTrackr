from crypto_tracker import CryptoPriceTracker
import time
import random

def simulate_historical_data():
    print("🚀 Creating demo data with multiple collection points...")
    print("This will give you charts and analysis immediately!")
    print("=" * 60)
    tracker = CryptoPriceTracker()
    for i in range(1, 6):
        print(f"\n📊 Collection {i}/5...")
        crypto_data = tracker.fetch_crypto_data(limit=50)
        if crypto_data:
            tracker.store_data(crypto_data)
            print(f"✅ Stored data for {len(crypto_data)} cryptocurrencies")
            btc_data = next((crypto for crypto in crypto_data 
                           if crypto.get('symbol', '').upper() == 'BTC'), None)
            if btc_data:
                price = btc_data.get('current_price', 0)
                change = btc_data.get('price_change_percentage_24h', 0)
                print(f"   BTC: ${price:,.2f} ({change:+.2f}%)")
        if i < 5:
            wait_time = random.randint(10, 30)  # Random wait 10-30 seconds
            print(f"⏱️  Waiting {wait_time} seconds before next collection...")
            time.sleep(wait_time)
    
    print("\n" + "=" * 60)
    print("🎉 Demo data collection complete!")
    print("Now generating visualizations and analysis...")
    print("\n1. 📈 Creating price trend charts...")
    major_cryptos = ['BTC', 'ETH', 'BNB', 'ADA']
    tracker.visualize_price_trends(major_cryptos, days=1)
    
    print("2. 📊 Analyzing volatility...")
    volatility_df = tracker.analyze_volatility(days=1)
    
    print("3. 🏆 Showing top gainers and losers...")
    tracker.visualize_gainers_losers()
    
    print("4. 💰 Market cap analysis...")
    tracker.market_cap_analysis()
    
    print("5. 📋 Generating comprehensive report...")
    tracker.generate_report(days=1)
    
    print("\n" + "=" * 60)
    print("🎊 DEMO COMPLETE!")
    print("\nYou now have:")
    print("✅ A working database with crypto data")
    print("✅ Multiple visualization charts")
    print("✅ Volatility analysis")
    print("✅ Gainers/losers analysis") 
    print("✅ Market cap breakdown")
    print("✅ Comprehensive report")
    
    print(f"\n🗃️  Database location: crypto_prices.db")
    print(f"📊 Total data points collected: ~{5 * 50} entries")
    
    return tracker

def show_quick_stats(tracker):
    """Show some quick statistics about collected data"""
    print("\n" + "=" * 40)
    print("📈 QUICK STATISTICS")
    print("=" * 40)
    df = tracker.get_all_data(days=1)
    
    if not df.empty:
        print(f"Total records: {len(df)}")
        print(f"Unique cryptocurrencies: {df['symbol'].nunique()}")
        print(f"Time span: {df['timestamp'].min()} to {df['timestamp'].max()}")
        latest_data = df.groupby('symbol').last().nlargest(5, 'market_cap')
        print(f"\nTop 5 by Market Cap:")
        for symbol, row in latest_data.iterrows():
            print(f"  {symbol}: ${row['market_cap']/1e9:.1f}B market cap")
    
    print("=" * 40)

if __name__ == "__main__":
    tracker = simulate_historical_data()
    show_quick_stats(tracker)
    
    print("\n🔄 Want to start real daily collection?")
    print("Run: python daily_collector.py")
    print("\n💡 Want to analyze specific cryptos?")
    print("Run: python -c \"from crypto_tracker import CryptoPriceTracker; t=CryptoPriceTracker(); t.visualize_price_trends(['BTC','ETH'], days=1)\"")