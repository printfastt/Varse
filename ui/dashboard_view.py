import sys
import yfinance as yf
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QWidget, QLineEdit, QPushButton, QApplication, QMainWindow, QLabel, QComboBox
from PyQt6 import uic
# import pandas as pd
import plotly.express as px
from PyQt6.QtWebEngineWidgets import QWebEngineView
# from matplotlib.pyplot import xlabel
from etrade_client.auth.etrade_auth import oauth
from etrade_client.accounts import Accounts


class DashboardView(QMainWindow):
    #declaring type for ide
    dateLabel: QLabel
    symbol1Input: QLineEdit
    symbol2Input: QLineEdit
    refreshButton: QPushButton
    qqqChartWidget: QWebEngineView
    spyChartWidget: QWebEngineView
    timeframeCombo: QComboBox


    def __init__(self):
        super().__init__()
        uic.loadUi("ui_files/dashboard_view.ui", self)

        # Set even split for charts
        total_height = self.chartsSplitter.height()
        half_height = total_height // 2
        self.chartsSplitter.setSizes([half_height, half_height])

        self.ChartView = ChartView(parent=self)
        self.EtradeView = EtradeView(parent=self)
        self.date = str(QDate.currentDate().toPyDate())

        #Configure
        self.dateLabel.setText(QDate.currentDate().toString())



class ChartView:
    def __init__(self, parent: DashboardView):
        self.parent: DashboardView = parent #prevents pycharm false underlines
        self.timeframe_intervals = {
            "1d": "1m",
            "5d": "5m",
            "1mo": "1h",
            "3mo": "1h",
            "1y": "1d",
            "2y": "1d",
            "5y": "1wk",
            "max": "1wk",
        }

        self.gridcolor = 'rgba(255, 255, 255, 0.1)'


        #user inputs
        self.timeframe_input = ""
        self.symbol1 = None
        self.symbol2 = None

        #wiring
        self.parent.refreshButton.clicked.connect(self.pressRefreshButton)

        #load charts on instantiation
        self.pressRefreshButton()

    def chartSymbol(self, symbol, widget):
        try:
            symbol_data = yf.download(symbol, period=self.timeframe_input, interval=self.timeframe_intervals[self.timeframe_input])
            symbol_closes = symbol_data[['Close']].dropna()
            symbol_closes.columns = symbol_closes.columns.droplevel('Ticker')
            overall_change = symbol_closes.iloc[-1]-symbol_closes.iloc[0]
            overall_change_pct = ((symbol_closes.iloc[-1] - symbol_closes.iloc[0]) / symbol_closes.iloc[0]) * 100
            modified_title = str(symbol) + " " + str(overall_change.iloc[0])
            fig = px.line(symbol_closes, y='Close', x=symbol_closes.index, title=modified_title)

            fig.update_layout(
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(l=0, r=0, b=0, t=30, pad=0),
                showlegend=False,
                plot_bgcolor="black",
                paper_bgcolor="black",
                yaxis=dict(
                    showgrid=True,
                    gridcolor=self.gridcolor,
                ),
                xaxis=dict(
                    showgrid=True,
                    gridcolor=self.gridcolor,
                    title=None
                )
            )

            fig.update_traces(line=dict(color='blue', width=3))
            html = f"""
            <html>
            <head>
                <style>
                    body {{
                        margin: 10px;
                        padding: 0;
                        background-color: black;
                    }}
                </style>
            </head>
            <body>
                {fig.to_html(include_plotlyjs='cdn', full_html=False)}
            </body>
            </html>
            """

            widget.setHtml(html)


        except Exception as e:
            print(e)

    def pressRefreshButton(self):
        symbol1_input = self.parent.symbol1Input.text().strip().upper()
        symbol2_input = self.parent.symbol2Input.text().strip().upper()
        self.timeframe_input = self.parent.timeframeCombo.currentText().strip()

        if symbol1_input:
            self.symbol1 = symbol1_input
        if symbol2_input:
            self.symbol2 = symbol2_input

        self.chartSymbol(self.symbol1, self.parent.spyChartWidget)
        self.chartSymbol(self.symbol2, self.parent.qqqChartWidget)

class EtradeView:
    def __init__(self, parent: DashboardView):
        self.parent: DashboardView = parent
        self.session, self.base_url = oauth()
        self.accounts = Accounts(self.session, self.base_url)


        self.accounts.account_list()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardView()
    window.show()
    sys.exit(app.exec())
