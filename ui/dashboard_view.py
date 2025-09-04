import sys
import yfinance as yf
from PIL.SpiderImagePlugin import isInt
from PyQt6.QtCore import QDate, QObject
from PyQt6.QtGui import QBrush, QColor, QAction, QActionGroup
from PyQt6.QtWidgets import QWidget, QLineEdit, QPushButton, QApplication, QMainWindow, QLabel, QComboBox, QSplitter, \
    QTableWidgetItem, QTableWidget
from PyQt6 import uic
import pandas as pd
import plotly.express as px
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.uic.Compiler.qtproxies import strict_getattr
import re
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
    actionSimple : QAction
    actionDynamic: QAction
    actionFull: QAction
    actionCustom: QAction

    #upper accounttotal footer
    todaysGainLossLabel: QLabel
    todaysGainLossPctLabel: QLabel
    totalGainLossLabel: QLabel
    totalGainLossPctLabel: QLabel
    totalMarketValueLabel: QLabel
    cashBalanceLabel: QLabel

    #lower accounttotal footer
    totalAssetsLabel: QLabel
    netAccountValueLabel: QLabel
    cashInvestableLabel: QLabel
    nonMarginableSecuritiesPPLabel: QLabel
    marginableSecuritiesPPLabel: QLabel
    marginLabel: QLabel


    def __init__(self):
        super().__init__()
        uic.loadUi("ui_files/dashboard_view.ui", self)

        total_height = self.chartsSplitter.height()
        half_height = total_height // 2
        self.chartsSplitter.setSizes([half_height, half_height])

        chart_components = {
            'refreshButton': self.refreshButton,
            'symbol1Input': self.symbol1Input,
            'symbol2Input': self.symbol2Input,
            'timeframeCombo': self.timeframeCombo,
            'spyChartWidget': self.spyChartWidget,
            'qqqChartWidget': self.qqqChartWidget
        }
        etrade_components = {
            'accountcomboBox': self.accountcomboBox,
            'holdingsTable': self.holdingsTable,
            'actionSimple': self.actionSimple,
            'actionDynamic': self.actionDynamic,
            'actionFull': self.actionFull,
            'actionCustom': self.actionCustom,

            #upper accounttotal footer
            'todaysGainLossLabel': self.todaysGainLossLabel,
            'todaysGainLossPctLabel': self.todaysGainLossPctLabel,
            'totalGainLossLabel': self.totalGainLossLabel,
            'totalGainLossPctLabel': self.totalGainLossPctLabel,
            'totalMarketValueLabel': self.totalMarketValueLabel,
            'cashBalanceLabel': self.cashBalanceLabel,

            #lower accounttotal footer
            'totalAssetsLabel': self.totalAssetsLabel,
            'netAccountValueLabel': self.netAccountValueLabel,
            'cashInvestableLabel': self.cashInvestableLabel,
            'nonMarginableSecuritiesPPLabel': self.nonMarginableSecuritiesPPLabel,
            'marginableSecuritiesPPLabel': self.marginableSecuritiesPPLabel,
            'marginLabel': self.marginLabel

        }

        self.ChartView = ChartView(chart_components)
        self.EtradeView = EtradeView(etrade_components)
        self.date = str(QDate.currentDate().toPyDate())

        #Configure
        self.dateLabel.setText(QDate.currentDate().toString())



class ChartView:
    def __init__(self, components):
        super().__init__()
        self.refreshButton = components['refreshButton']
        self.symbol1Input = components['symbol1Input']
        self.symbol2Input = components['symbol2Input']
        self.timeframeCombo = components['timeframeCombo']
        self.spyChartWidget = components['spyChartWidget']
        self.qqqChartWidget = components['qqqChartWidget']
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
        self.refreshButton.clicked.connect(self.press_refresh_button)

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
        symbol1_input = self.symbol1Input.text().strip().upper()
        symbol2_input = self.symbol2Input.text().strip().upper()
        self.timeframe_input = self.timeframeCombo.currentText().strip()

        if symbol1_input:
            self.symbol1 = symbol1_input
        if symbol2_input:
            self.symbol2 = symbol2_input

        self.chart_symbol(self.symbol1, self.spyChartWidget)
        self.chart_symbol(self.symbol2, self.qqqChartWidget)

class EtradeView(QObject):
    viewModeGroup: QActionGroup
    def __init__(self, components):
        super().__init__()
        #upper accounttotal footer
        self.todaysGainLossLabel = components['todaysGainLossLabel']
        self.todaysGainLossPctLabel = components['todaysGainLossPctLabel']
        self.totalGainLossLabel = components['totalGainLossLabel']
        self.totalGainLossPctLabel = components['totalGainLossPctLabel']
        self.totalMarketValueLabel = components['totalMarketValueLabel']
        self.cashBalanceLabel = components['cashBalanceLabel']

        #lower accounttotal footer
        self.totalAssetsLabel = components['totalAssetsLabel']
        self.netAccountValueLabel = components['netAccountValueLabel']
        self.cashInvestableLabel = components['cashInvestableLabel']
        self.nonMarginableSecuritiesPPLabel = components['nonMarginableSecuritiesPPLabel']
        self.marginableSecuritiesPPLabel = components['marginableSecuritiesPPLabel']
        self.marginLabel = components['marginLabel']

        self.accountcomboBox = components['accountcomboBox']
        self.holdingsTable = components['holdingsTable']
        self.actionSimple = components['actionSimple']
        self.actionDynamic = components['actionDynamic']
        self.actionFull = components['actionFull']
        self.actionCustom = components['actionCustom']
        self.viewModeGroup = QActionGroup(self)

        #holdingsTable settings
        self.holdingsTable.horizontalHeader().setStretchLastSection(True)

        self.session, self.base_url = oauth()
        self.accounts_manager = AccountsManager(self.session, self.base_url)
        self.current_account_index = None
        self._init_accountscomboBox()
        self._init_action_group()
        self.populate_portfolio_table()
        self.populate_accounttables_footer()



    def _init_accountscomboBox(self):
        for account_index, account in enumerate(self.accounts_manager.accounts_list):
            self.accountcomboBox.addItem(account.account_info.get('accountDesc') + " - " + str(account.account_info.get('accountId')), account_index)
        start_index = self.accounts_manager.num_of_accounts - 1
        self.accountcomboBox.setCurrentIndex(start_index)
        self.current_account_index = start_index
        self.accountcomboBox.currentIndexChanged.connect(self._on_account_select_changed)

    def _init_action_group(self):
        self.viewModeGroup.setExclusive(True)
        self.viewModeGroup.addAction(self.actionSimple)
        self.viewModeGroup.addAction(self.actionDynamic)
        self.viewModeGroup.addAction(self.actionFull)
        self.viewModeGroup.addAction(self.actionCustom)
        self.viewModeGroup.triggered.connect(self._on_action_group_viewmode_change)
        self.actionDynamic.setChecked(True)

    def _on_account_select_changed(self, index):
        # self.accountcomboBox.setCurrentIndex(index)
        self.current_account_index = index
        self.populate_portfolio_table()
        self.populate_accounttables_footer()

    def _on_action_group_viewmode_change(self):
        self.populate_portfolio_table()

#NOTE NEED TO FINISH FORMATTING
    def populate_portfolio_table(self):

        def _portfolio_view_select_adjust(df):
            selected_action = self.viewModeGroup.checkedAction()
            if selected_action:
                if selected_action.objectName() == 'actionSimple' or selected_action.objectName() == 'actionDynamic':
                    df = df[['symbolDescription', 'lastTrade', 'change', 'quantity', 'daysGain', 'daysGainPct', 'totalGain', 'totalGainPct', 'pctOfPortfolio']]
                elif selected_action.objectName() == 'actionFull':
                    pass
                elif selected_action.objectName() == 'actionCustom':
                    pass
                return df
            else:
                return df

        def _format_columns_with_suffix(data, suffix="%"):
            if isinstance(data, pd.Series):
                return data.apply(lambda x: f"{x:.2f}{suffix}" if pd.notnull(x) else "")
            elif isinstance(data, pd.DataFrame):
                return data.applymap(lambda x: f"{x:.2f}{suffix}" if pd.notnull(x) else "")
            else:
                raise TypeError("Input must be a pandas Series or DataFrame.")

        def _formatter():
            positions_copy = positions.copy()
            if self.viewModeGroup.checkedAction().objectName() == 'actionDynamic':
                positions_copy['lastTrade(d)'] = positions_copy.apply(
                    lambda row: f"{row['lastTrade']:.2f} ({row['change']:+.2f})", axis=1
                )
                positions_copy = positions_copy.drop(columns=['lastTrade', 'change'])

                positions_copy['dayChange'] = positions_copy.apply(
                    lambda row: f"{row['daysGainPct']:.2f}% ({row['daysGain']:+.2f})", axis=1
                )
                positions_copy = positions_copy.drop(columns=['daysGainPct', 'daysGain'])

                cols = positions_copy.columns.tolist()
                cols.insert(1, cols.pop(cols.index('lastTrade(d)')))
                cols.insert(2, cols.pop(cols.index('dayChange')))
                positions_copy = positions_copy[cols]

                # positions_copy['totalGainPct'] = _format_columns_with_suffix(positions_copy['totalGainPct'], '%')
                # positions_copy['pctOfPortfolio'] = _format_columns_with_suffix(positions_copy['totalGainPct'], '%')

            return positions_copy

        def _plot():
            positions_copy = _formatter()
            def _check_if_colored(item, j, value):
                col_name = positions_copy.columns[j]
                if 'Pct' in col_name or 'Gain' in col_name or 'change' in col_name:
                    if isinstance(value, (int, float, complex)):
                        if value > 0:
                            item.setForeground(QBrush(QColor('green')))
                        elif value < 0:
                            item.setForeground(QBrush(QColor('red')))

                elif col_name == 'lastTrade(d)' or col_name == 'dayChange':
                    match = re.search(r'\(([-+]?[\d.]+)\)', str(value))
                    if match:
                        try:
                            change_val = float(match.group(1))
                            if change_val > 0:
                                item.setForeground(QBrush(QColor('green')))
                            elif change_val < 0:
                                item.setForeground(QBrush(QColor('red')))
                        except ValueError:
                            pass


            self.holdingsTable.setRowCount(len(positions_copy))
            self.holdingsTable.setColumnCount(len(positions_copy.columns))
            self.holdingsTable.setHorizontalHeaderLabels(positions_copy.columns)
            for i in range(len(positions_copy)):
                for j in range(len(positions_copy.columns)):
                    value = positions_copy.iloc[i,j]
                    item = QTableWidgetItem(str(value))

                    _check_if_colored(item, j, value)

                    self.holdingsTable.setItem(i, j, item)

            self.holdingsTable.resizeColumnsToContents()

        positions_full = self.accounts_manager.accounts_list[self.current_account_index].positions.copy()
        positions = _portfolio_view_select_adjust(positions_full)
        _plot()

    def _format_gain_loss_label(self, label, value):
        base_style = "background-color: transparent; border: none;"
        if value > 0:
            label.setStyleSheet(base_style + "color: green;")
        elif value < 0:
            label.setStyleSheet(base_style + "color: red;")
        else:
            label.setStyleSheet(base_style)

    def populate_accounttables_footer(self):
        accounttotals = self.accounts_manager.accounts_list[self.current_account_index].accounttotals.copy()
        balances = self.accounts_manager.accounts_list[self.current_account_index].balances.copy()

        # Set text and apply color formatting for gain/loss labels
        todays_gain_loss = accounttotals.loc['todaysGainLoss']
        todays_gain_loss_pct = accounttotals.loc['todaysGainLossPct']
        total_gain_loss = accounttotals.loc['totalGainLoss']
        total_gain_loss_pct = accounttotals.loc['totalGainLossPct']

        self.todaysGainLossLabel.setText(f"${todays_gain_loss:.2f}")
        self._format_gain_loss_label(self.todaysGainLossLabel, todays_gain_loss)
        
        self.todaysGainLossPctLabel.setText(f"{todays_gain_loss_pct:.2f}%")
        self._format_gain_loss_label(self.todaysGainLossPctLabel, todays_gain_loss_pct)
        
        self.totalGainLossLabel.setText(f"${total_gain_loss:.2f}")
        self._format_gain_loss_label(self.totalGainLossLabel, total_gain_loss)
        
        self.totalGainLossPctLabel.setText(f"{total_gain_loss_pct:.2f}%")
        self._format_gain_loss_label(self.totalGainLossPctLabel, total_gain_loss_pct)

        # These labels remain unformatted
        self.totalMarketValueLabel.setText(f"${accounttotals.loc['totalMarketValue']:.2f}")
        self.cashBalanceLabel.setText(f"${accounttotals.loc['cashBalance']:.2f}")

        self.nonMarginableSecuritiesPPLabel.setText(f"${balances.loc['netCash']:.2f}")
        self.netAccountValueLabel.setText(f"${accounttotals.loc['totalMarketValue']+accounttotals.loc['cashBalance']:.2f}")
        self.marginableSecuritiesPPLabel.setText(f"${balances.loc['marginBuyingPower']:.2f}")
        self.marginLabel.setText(f"${balances.loc['marginBalance']:.2f}") #MAY NEED TO CHANGE
        self.cashInvestableLabel.setText(f"${balances.loc['cashAvailableForInvestment']:.2f}")
        #need to add totalAssetsLabel.


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardView()
    window.show()
    sys.exit(app.exec())

