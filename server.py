from flask import Flask, render_template, request, jsonify, session
from fyers_apiv3 import fyersModel
import pandas as pd
import datetime
import logging

# Initialize Flask App
app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Required for session management

# Configure logging
logging.basicConfig(level=logging.INFO)

# ----------------------- Step 1: Generate Authorization URL -----------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_auth_url', methods=['POST'])
def get_auth_url():
    data = request.json
    client_id = data.get("client_id")
    secret_key = data.get("secret_key")

    if not client_id or not secret_key:
        return jsonify({"error": "Client ID and Secret Key are required!"}), 400

    # Save credentials in session
    session['client_id'] = client_id
    session['secret_key'] = secret_key

    redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"
    response_type = "code"

    session_model = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type=response_type
    )

    auth_url = session_model.generate_authcode()
    return jsonify({"auth_url": auth_url})

# ----------------------- Step 2: Fetch Access Token -----------------------
@app.route('/exchange_code', methods=['POST'])
def exchange_code():
    data = request.json
    auth_code = data.get("auth_code")

    if not auth_code:
        return jsonify({"error": "Authorization code is required!"}), 400

    client_id = session.get("client_id")
    secret_key = session.get("secret_key")

    if not client_id or not secret_key:
        return jsonify({"error": "Client ID or Secret Key missing! Please re-enter credentials."}), 400

    redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"
    response_type = "code"
    grant_type = "authorization_code"

    try:
        session_model = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            response_type=response_type,
            grant_type=grant_type
        )

        session_model.set_token(auth_code)
        response = session_model.generate_token()

        logging.info(f"Fyers API Response: {response}")

        if 'access_token' in response:
            access_token = response['access_token']
            session['access_token'] = access_token
            return jsonify({"access_token": access_token})
        else:
            return jsonify({"error": "Failed to generate access token!", "details": response}), 400

    except Exception as e:
        logging.error(f"Error exchanging code for token: {str(e)}")
        return jsonify({"error": "Exception occurred!", "details": str(e)}), 500

# ----------------------- Step 3: Run Trading Strategy -----------------------
def fetch_historical_data(fyers, symbol):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    past_20_days = yesterday - datetime.timedelta(days=19)

    data = {
        "symbol": symbol,
        "resolution": "D",
        "date_format": "1",
        "range_from": past_20_days.strftime('%Y-%m-%d'),
        "range_to": yesterday.strftime('%Y-%m-%d'),
        "cont_flag": "1"
    }

    try:
        response = fyers.history(data=data)
        logging.info(f"Historical Data Response for {symbol}: {response}")

        if response and 'candles' in response:
            df = pd.DataFrame(response['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        logging.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return pd.DataFrame()

def fetch_live_ltp(fyers, symbols):
    data = {"symbols": ",".join(symbols)}
    
    try:
        response = fyers.quotes(data=data)
        logging.info(f"LTP Data Response: {response}")

        if response and response.get("code") == 200:
            return {s.get("n"): s.get("v", {}).get("lp", "N/A") for s in response.get("d", [])}
        return {symbol: "N/A" for symbol in symbols}

    except Exception as e:
        logging.error(f"Error fetching LTP: {str(e)}")
        return {symbol: "N/A" for symbol in symbols}

@app.route('/run_strategy', methods=['POST'])
def run_strategy():
    client_id = session.get("client_id")
    access_token = session.get("access_token")

    if not client_id or not access_token:
        return jsonify({"error": "Missing credentials! Please authenticate first."}), 400

    fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token)

    symbols = ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:INFY-EQ", "NSE:ICICIBANK-EQ",
    "NSE:HDFCBANK-EQ", "NSE:SHRIRAMCIT-EQ", "NSE:KANSAINER-EQ",
    "NSE:BAJAJHLDNG-EQ", "NSE:BALAMINES-EQ", "NSE:ITC-EQ", "NSE:KOTAKBANK-EQ",
    "NSE:SBIN-EQ", "NSE:BHARTIARTL-EQ", "NSE:HCLTECH-EQ",
    "NSE:ASIANPAINT-EQ", "NSE:LT-EQ", "NSE:HINDUNILVR-EQ", "NSE:AXISBANK-EQ",
    "NSE:BAJFINANCE-EQ", "NSE:MARUTI-EQ", "NSE:SUNPHARMA-EQ", "NSE:ULTRACEMCO-EQ"
]

    ltp_data = fetch_live_ltp(fyers, symbols)

    results = {}
    for symbol in symbols:
        df = fetch_historical_data(fyers, symbol)
        if df.empty:
            results[symbol] = "No Data Available"
            continue

        try:
            twenty_days_high = df['high'].max()
            yesterday_close = df['close'].iloc[-1]
            ltp = float(ltp_data.get(symbol, "0"))  # Default to 0 if no LTP

            percent_diff_20d = ((ltp - twenty_days_high) / twenty_days_high) * 100 if twenty_days_high != 0 else 0
            percent_diff_yclose = ((ltp - yesterday_close) / yesterday_close) * 100 if yesterday_close != 0 else 0
            buy_signal = "✅ Buy" if ltp > twenty_days_high else "❌ Hold"
            target_price = ltp * 1.05
            stop_loss = ltp * 0.99
            trailing_stop_loss = target_price * 0.98

            results[symbol] = {
                "20D High": round(twenty_days_high, 2),
                "Yesterday Close": round(yesterday_close, 2),
                "LTP": round(ltp, 2),
                "% Diff (Y.Close)": f"{percent_diff_yclose:.2f}%",
                "% Diff (20D High)": f"{percent_diff_20d:.2f}%",
                "Signal": buy_signal,
                "Target Price": round(target_price, 2),
                "Stop Loss": round(stop_loss, 2),
                "Trailing SL": round(trailing_stop_loss, 2)
            }

        except Exception as e:
            logging.error(f"Error processing strategy for {symbol}: {str(e)}")
            results[symbol] = {"error": "Error processing strategy"}

    logging.info(f"Strategy Results: {results}")
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
