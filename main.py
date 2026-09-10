import time
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

class CloudTradingBot:
    def __init__(self, symbol="EURUSD", lot=0.01):
        self.symbol = symbol
        self.lot = lot

    def initialize_mt5(self):
        # تهيئة الاتصال بمنصة ميتاتريدر 5
        if not mt5.initialize():
            print("فشل الاتصال بمنصة MT5، رمز الخطأ:", mt5.last_error())
            return False
        print("تم الاتصال بمنصة MetaTrader 5 بنجاح على السحابة!")
        return True

    def get_market_data(self, timeframe=mt5.TIMEFRAME_M15, num_candles=100):
        # جلب البيانات الحية للأسعار من المنصة
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, num_candles)
        if rates is None:
            print("فشل في جلب بيانات الأسعار.")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def calculate_indicators(self, df):
        # حساب المتوسطات ومؤشر الزخم RSI
        df['Short_MA'] = df['Close'].rolling(window=10).mean()
        df['Long_MA'] = df['Close'].rolling(window=50).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df

    def run(self):
        if not self.initialize_mt5():
            return

        print(f"البوت يعمل الآن ويراقب زوج العملات: {self.symbol}...")
        
        try:
            while True:
                df = self.get_market_data()
                if df is not None:
                    df = self.calculate_indicators(df)
                    latest = df.iloc[-1]
                    
                    # شروط اتخاذ القرار بناءً على الخوارزمية
                    if latest['Short_MA'] > latest['Long_MA'] and latest['RSI'] < 70:
                        print(f"إشارة شراء قوية لـ {self.symbol} عند السعر: {latest['Close']}")
                        # هنا يمكن إضافة كود تنفيذ أمر الشراء الفعلي عبر MT5
                        
                    elif latest['Short_MA'] < latest['Long_MA'] and latest['RSI'] > 30:
                        print(f"إشارة بيع قوية لـ {self.symbol} عند السعر: {latest['Close']}")
                        # هنا يمكن إضافة كود تنفيذ أمر البيع الفعلي عبر MT5
                    else:
                        print(f"السعر الحالي: {latest['Close']} | جاري الانتظار ومراقبة السوق...")
                
                # الانتظار لمدة دقيقة قبل فحص السوق مرة أخرى
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("تم إيقاف البوت.")
            mt5.shutdown()

if __name__ == "__main__":
    bot = CloudTradingBot(symbol="EURUSD", lot=0.01)
    bot.run()
