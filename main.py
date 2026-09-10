import time
import os
import requests
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

# بيانات حساب التداول (حساب MetaQuotes-Demo الجديد)
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "112423048"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "@c0yNuTd")
MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")

# بيانات بوت تيليجرام (قم بوضع التوكن الخاص بك هنا أو عبر متغيرات السحابة)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ضع_توكن_البوت_هنا")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "204891274")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ في إرسال تيليجرام: {e}")

class InstitutionalTelegramTradingBot:
    def __init__(self, symbol="EURUSD", lot=0.1):
        self.symbol = symbol
        self.lot = lot

    def connect_broker(self):
        if not mt5.initialize():
            msg = f"❌ فشل تهيئة MT5، رمز الخطأ: {mt5.last_error()}"
            print(msg)
            send_telegram_message(msg)
            return False
        
        authorized = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
        if not authorized:
            msg = f"❌ فشل تسجيل الدخول لحساب MT5 رقم {MT5_LOGIN}، الخطأ: {mt5.last_error()}"
            print(msg)
            send_telegram_message(msg)
            mt5.shutdown()
            return False
            
        success_msg = f"✅ تم الاتصال بنجاح بحساب التداول رقم: {MT5_LOGIN} على سيرفر {MT5_SERVER}!"
        print(success_msg)
        send_telegram_message(success_msg)
        return True

    def get_market_data(self, timeframe=mt5.TIMEFRAME_M15, num_candles=100):
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, num_candles)
        if rates is None:
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def calculate_strategy(self, df):
        df['EMA_Fast'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_Slow'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df

    def execute_order(self, order_type, price, current_rsi):
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None or not symbol_info.visible:
            mt5.symbol_select(self.symbol, True)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.lot,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Institutional Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"❌ فشل تنفيذ الصفقة لـ {self.symbol}، الكود: {result.retcode}"
            print(error_msg)
            send_telegram_message(error_msg)
        else:
            action_name = "شراء (BUY)" if order_type == mt5.ORDER_TYPE_BUY else "بيع (SELL)"
            success_msg = (
                f"🚨 *تم تنفيذ صفقة جديدة بنجاح!*\n"
                f"🔹 النوع: {action_name}\n"
                f"🔹 الزوج: {self.symbol}\n"
                f"🔹 السعر: {price}\n"
                f"🔹 مؤشر RSI: {round(current_rsi, 2)}\n"
                f"🔹 رقم الأوامر: {result.order}"
            )
            print(success_msg)
            send_telegram_message(success_msg)

    def monitor_positions(self):
        # تتبع الصفقات المفتوحة وحساب الأرباح والخسائر وإرسالها
        positions = mt5.positions_get(symbol=self.symbol)
        if positions:
            for pos in positions:
                profit = pos.profit
                status_msg = f"📊 *تحديث الصفقة المفتوحة ({self.symbol}):*\nالربح / الخسارة الحالية: `{profit} USD`"
                print(status_msg)
                # يمكنك تفعيل إرسال الحالة دورياً إذا أردت

    def run(self):
        if not self.connect_broker():
            return

        print(f"🤖 البوت يعمل ويراقب السوق على زوج: {self.symbol}...")
        send_telegram_message(f"🚀 بدأ بوت التداول الآلي بالعمل على السحابة لزوج {self.symbol}!")

        try:
            while True:
                df = self.get_market_data()
                if df is not None:
                    df = self.calculate_strategy(df)
                    latest = df.iloc[-1]
                    prev = df.iloc[-2]

                    # فحص الصفقات الحالية
                    self.monitor_positions()

                    # شروط الشراء
                    if prev['EMA_Fast'] <= prev['EMA_Slow'] and latest['EMA_Fast'] > latest['EMA_Slow'] and latest['RSI'] < 60:
                        price = mt5.symbol_info_tick(self.symbol).ask
                        self.execute_order(mt5.ORDER_TYPE_BUY, price, latest['RSI'])

                    # شروط البيع
                    elif prev['EMA_Fast'] >= prev['EMA_Slow'] and latest['EMA_Fast'] < latest['EMA_Slow'] and latest['RSI'] > 40:
                        price = mt5.symbol_info_tick(self.symbol).bid
                        self.execute_order(mt5.ORDER_TYPE_SELL, price, latest['RSI'])
                    else:
                        print(f"⏳ السعر الحالي: {latest['Close']} | جاري رصد الفرص...")

                # فحص السوق كل دقيقة
                time.sleep(60)

        except KeyboardInterrupt:
            send_telegram_message("⚠️ تم إيقاف بوت التداول على السحابة.")
            mt5.shutdown()

if __name__ == "__main__":
    bot = InstitutionalTelegramTradingBot(symbol="EURUSD", lot=0.1)
    bot.run()
مم
