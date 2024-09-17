# filename: ytd_gain_comparison.py

# Stock prices
stock_prices = {
    'MSFT': {'start_price': 368.85, 'end_price': 431.34},
    'TSLA': {'start_price': 248.42, 'end_price': 226.78}
}

# Calculate YTD gain
def calculate_ytd_gain(start_price, end_price):
    return ((end_price - start_price) / start_price) * 100

# Calculate YTD gains for MSFT and TSLA
ytd_gains = {}
for stock, prices in stock_prices.items():
    ytd_gains[stock] = calculate_ytd_gain(prices['start_price'], prices['end_price'])

# Print the YTD gains
for stock, gain in ytd_gains.items():
    print(f"{stock} YTD Gain: {gain:.2f}%")

# Compare the YTD gains
if ytd_gains['MSFT'] > ytd_gains['TSLA']:
    print("MSFT has a higher YTD gain than TSLA.")
elif ytd_gains['MSFT'] < ytd_gains['TSLA']:
    print("TSLA has a higher YTD gain than MSFT.")
else:
    print("MSFT and TSLA have the same YTD gain.")