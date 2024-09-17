# filename: stock_prices.py
import yfinance as yf
from datetime import datetime

# Define the stock symbols and dates
stocks = ['MSFT', 'TSLA']
start_date = '2024-01-01'
end_date = '2024-09-17'

# Fetch the stock prices
stock_data = {}
for stock in stocks:
    ticker = yf.Ticker(stock)
    hist = ticker.history(start=start_date, end=end_date)
    stock_data[stock] = {
        'start_price': hist['Close'].iloc[0],
        'end_price': hist['Close'].iloc[-1]
    }

# Print the stock prices
for stock, prices in stock_data.items():
    print(f"{stock} - Start Price: {prices['start_price']}, End Price: {prices['end_price']}")