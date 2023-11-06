import time
import pandas as pd
import yfinance as yf
import finta
import pandas_ta as ta

def download_stock_data(ticker, start, end):
    return yf.download(ticker, start=start, end=end)

def calculate_indicators(data):
    # Use TTM Trend from pandas_ta with length=40
    ttm_trend = ta.ttm_trend(data['High'], data['Low'], data['Close'], length=40)
    data['TTM_TREND'] = ttm_trend

    # Use SQZMI from finta with period=24
    ohlc_data = data[['Open', 'High', 'Low', 'Close']]
    sqzmi = finta.TA.SQZMI(ohlc_data, period=24)
    data['SQZMI'] = sqzmi

    return data

def initialize_columns(data):
    data['Buy_Signal'] = 0
    data['Sell_Signal'] = 0
    data['Portfolio_Value'] = 0

def evaluate_signals(data):
    data['Buy_Condition'] = data['TTM_TREND'] > data['SQZMI']
    data['Sell_Condition'] = data['TTM_TREND'] < data['SQZMI']

def run_simulation(data, initial_cash):
    cash = initial_cash
    stock_quantity = 0
    transactions = []
    last_action = None
    # Start at the index where both indicators first have non-NaN values
    start_index = max(data['TTM_TREND'].first_valid_index(), data['SQZMI'].first_valid_index())
    # Convert the Timestamp to its integer-based location
    start_index = data.index.get_loc(start_index)

    for i in range(start_index, len(data)):
        close_price = data['Close'].iloc[i]

        if data['Buy_Condition'].iloc[i] and cash > 0 and last_action != 'Buy':
            stock_quantity = cash // close_price
            cash -= stock_quantity * close_price
            transactions.append([data.index[i], 'Buy', close_price, stock_quantity, cash, cash + stock_quantity * close_price])
            data.at[data.index[i], 'Buy_Signal'] = 1
            last_action = 'Buy'

        elif data['Sell_Condition'].iloc[i] and stock_quantity > 0 and last_action != 'Sell':
            cash += stock_quantity * close_price
            transactions.append([data.index[i], 'Sell', close_price, 0, cash, cash])
            stock_quantity = 0
            data.at[data.index[i], 'Sell_Signal'] = 1
            last_action = 'Sell'

        data.at[data.index[i], 'Portfolio_Value'] = cash + stock_quantity * close_price

    return pd.DataFrame(transactions, columns=['Date', 'Action', 'Price', 'Quantity', 'Cash', 'Portfolio_Value'])

def main():
    tickers_df = pd.read_csv('tickers.csv')
    tickers = tickers_df['Ticker'].tolist()
    number_of_tickers = len(tickers)

    individual_stock_return = {}
    initial_investment_per_stock = 100000
    initial_total_investment = initial_investment_per_stock * number_of_tickers

    start_date = '2018-10-30'
    end_date = '2023-10-30'

    total_portfolio_value = 0
    transactions_dict = {}

    for ticker in tickers:
        initial_cash = 100000  # Resetting initial_cash for each ticker
        try:
            data = download_stock_data(ticker, start_date, end_date)
            if data.empty:
                print(f"Failed to download data for {ticker}. Skipping.")
                continue

            data = calculate_indicators(data)
            initialize_columns(data)
            evaluate_signals(data)
            transactions = run_simulation(data, initial_cash)
            initial_stock_value = transactions['Price'].iloc[0] * transactions['Quantity'].iloc[0]
            final_stock_value = transactions['Portfolio_Value'].iloc[-1]
            stock_return_percent = ((final_stock_value - initial_stock_value) / initial_stock_value) * 100
            individual_stock_return[ticker] = stock_return_percent

            final_portfolio_value = transactions['Portfolio_Value'].iloc[-1]
            total_portfolio_value += final_portfolio_value

            transactions_dict[ticker] = transactions
        except Exception as e:
            print(f"An exception occurred for {ticker}: {e}. Skipping.")

    for ticker, transactions in transactions_dict.items():
        transactions.to_csv(f"{ticker}_transactions.csv", index=False)

    print(f"Total Portfolio Value: {total_portfolio_value:.2f}")
    total_return_percent = ((total_portfolio_value - initial_total_investment) / initial_total_investment) * 100
    print(f"Total Return: {total_return_percent:.2f}%")
    for ticker, return_percent in individual_stock_return.items():
        print(f"{ticker} Return: {return_percent:.2f}%")

if __name__ == "__main__":
    main()
