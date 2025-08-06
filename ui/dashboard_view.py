import sys
import yfinance as yf
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QWidget, QLineEdit, QPushButton, QApplication, QMainWindow, QLabel, QComboBox, QSplitter, \
    QTableWidgetItem, QTableWidget
from PyQt6 import uic
# import pandas as pd
import plotly.express as px
from PyQt6.QtWebEngineWidgets import QWebEngineView
# from matplotlib.pyplot import xlabel
from etrade_client.auth.etrade_auth import oauth
from etrade_client.accountsmanager import AccountsManager


class DashboardView(QMainWindow):
    #declaring type for ide
    dateLabel: QLabel
    symbol1Input: QLineEdit
    symbol2Input: QLineEdit
    refreshButton: QPushButton
    qqqChartWidget: QWebEngineView
    spyChartWidget: QWebEngineView
    timeframeCombo: QComboBox
    chartsSplitter: QSplitter
    holdingsTable: QTableWidget
    accountcomboBox: QComboBox


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
        self.parent.refreshButton.clicked.connect(self.press_refresh_button)

        #load charts on instantiation
        self.press_refresh_button()

    def chart_symbol(self, symbol, widget):
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

    def press_refresh_button(self):
        symbol1_input = self.parent.symbol1Input.text().strip().upper()
        symbol2_input = self.parent.symbol2Input.text().strip().upper()
        self.timeframe_input = self.parent.timeframeCombo.currentText().strip()

        if symbol1_input:
            self.symbol1 = symbol1_input
        if symbol2_input:
            self.symbol2 = symbol2_input

        self.chart_symbol(self.symbol1, self.parent.spyChartWidget)
        self.chart_symbol(self.symbol2, self.parent.qqqChartWidget)

class EtradeView:
    def __init__(self, parent: DashboardView):
        self.parent: DashboardView = parent
        self.session, self.base_url = oauth()
        self.accounts_manager = AccountsManager(self.session, self.base_url)
        # self.selected_account = self.accounts_manager.num_of_accounts-1

        #wiring
        self.parent.accountcomboBox.currentIndexChanged.connect(self.on_selection_changed)

        self._populate_accountscomboBox()
        self.on_selection_changed(self.accounts_manager.num_of_accounts-1)

    def _populate_accountscomboBox(self):
        for account_index, account in enumerate(self.accounts_manager.accounts_list):
            self.parent.accountcomboBox.addItem(account.account_info.get('accountDesc') + " - " + str(account.account_info.get('accountId')), account_index)

    def on_selection_changed(self, index):
        # account_name = self.combo.itemData(index)
        self.populate_portfolio_table(self.accounts_manager.accounts_list[index].positions, self.parent.holdingsTable)

    @staticmethod
    def populate_portfolio_table(positions, widget):
        widget.setRowCount(len(positions))
        widget.setColumnCount(len(positions.columns))
        widget.setHorizontalHeaderLabels(positions.columns)

        for i in range(len(positions)):
            for j in range(len(positions.columns)):
                value = str(positions.iloc[i,j])
                widget.setItem(i, j, QTableWidgetItem(value))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardView()
    window.show()
    sys.exit(app.exec())

