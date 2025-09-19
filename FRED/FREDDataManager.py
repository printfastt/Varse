
class FREDDataManager:
    def __init__(self):
        self.fred = None
        self.indicators = {
            'Real GDP': 'GDP',
            'Real GDP Growth Rate':'A191RL1Q225SBEA',
            'Industrial Production':'INDPRO',
            'Unemployment Rate': 'UNRATE',
            'Inflation (CPI)': 'CPIAUCSL',
            'Core CPI': 'CPILFESL',
            'Fed Funds Rate': 'FEDFUNDS',
            '10-Year Treasury': 'GS10',
            '2-Year Treasury': 'GS2',
            '30-Year Mortgage Rate':'MORTGAGE30US',
            'Commercial Bank Prime Rate':'MPRIME',
            'AAA Corporate B Spread':'AAA10Y',
            'High Yield Spread':'BAMLH0A0HYM2',
            'Housing Starts':'HOUST',
            'New Home Sales': 'HSN1F',
            'Dollar Index': 'DTWEXBGS',         
            'Oil Prices': 'DCOILWTICO',
            'Consumer Sentiment': 'UMCSENT',
            'VIX': 'VIXCLS',
            'Imports': 'IMPGS',
            'Exports': 'EXPGS'
        }
        self.EconomicViewRowData = {}

        try:
            from fredapi import Fred
            from .config import FRED_API_KEY
            self.fred = Fred(api_key=FRED_API_KEY)
        except ImportError:
            print("Error importing FRED API library")
        except Exception as e:
            print("Error initializing FRED API:", e)

        for name, series_id in self.indicators.items():
            try:
                data = self.fred.get_series(series_id)
                self.process_data(data, name)
            except Exception as e:
                print(f"Error fetching {name}: {e}")

    def process_data(self,data, name):
        if not data.empty:
            values = data.iloc[-1:-6:-1].values.tolist()
            latest_value = values[0]
            latest_date = data.index[-1].strftime('%Y-%m-%d')
            self.EconomicViewRowData[name] = {
                'current': latest_value,
                'change': round(data.iloc[-2] - latest_value,2),
                'change_pct': round((data.iloc[-2] - latest_value) / latest_value * 100,2),
                'date': latest_date,
                'values': values,
                'last_3': values[1:4:1],
            }

        else:
            self.EconomicViewRowData[name] = {
                'value': "N/A",
                'change': "N/A",
                'change_pct': "N/A",
                'date': "N/A",
                'values': [],
                'last_3': []
            }


