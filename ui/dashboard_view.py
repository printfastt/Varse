import sys
import yfinance as yf
from PIL.SpiderImagePlugin import isInt
from PyQt6.QtCore import QDate, QObject, Qt, QThread
from PyQt6.QtGui import QBrush, QColor, QAction, QActionGroup
from PyQt6.QtWidgets import QWidget, QLineEdit, QPushButton, QApplication, QMainWindow, QLabel, QComboBox, QSplitter, \
    QTableWidgetItem, QTableWidget, QFrame, QMenu, QWidgetAction, QHBoxLayout, QVBoxLayout
from PyQt6 import uic
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
import pandas as pd
import plotly.express as px
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.uic.Compiler.qtproxies import strict_getattr
import re
# from matplotlib.pyplot import xlabel
from etrade_client.auth.etrade_auth import oauth
from etrade_client.accountsmanager import AccountsManager
from etrade_client.pollworker import PollWorker
from datetime import datetime, timedelta

class MiniChart(QWidget):
    def __init__(self, values, width=60, height=20):
        super().__init__()
        self.values = values
        self.setFixedSize(width, height)
        
    def paintEvent(self, event):
        if not self.values or len(self.values) < 2:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        margin = 2
        chart_width = self.width() - 2 * margin
        chart_height = self.height() - 2 * margin
        
        min_val = min(self.values)
        max_val = max(self.values)
        val_range = max_val - min_val if max_val != min_val else 1
        
        points = []
        for i, value in enumerate(self.values):
            x = margin + (i / (len(self.values) - 1)) * chart_width
            y = margin + chart_height - ((value - min_val) / val_range) * chart_height
            points.append((x, y))
        
        pen = QPen(QColor('#4a90e2'), 1)
        painter.setPen(pen)
        
        for i in range(len(points) - 1):
            painter.drawLine(int(points[i][0]), int(points[i][1]), 
                           int(points[i+1][0]), int(points[i+1][1]))

class EconomicRow(QFrame):
    def __init__(self, name, data):
        super().__init__()
        self.name = name
        self.data = data
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
                border: none;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        # Name
        name_label = QLabel(self.name)
        name_label.setFont(QFont("Consolas", 9))
        name_label.setFixedWidth(70)
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Current value
        current_text = f"{self.data['current']:.2f}"
        if 'Treas' in self.name or 'CPI' in self.name or 'Fed' in self.name:
            current_text += "%"
        current_label = QLabel(current_text)
        current_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        current_label.setFixedWidth(60)
        current_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Change
        change_text = f"{self.data['change']:+.2f}"
        change_label = QLabel(change_text)
        change_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        change_label.setFixedWidth(50)
        change_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        if self.data['change'] > 0:
            change_label.setStyleSheet("color: green;")
        elif self.data['change'] < 0:
            change_label.setStyleSheet("color: red;")
        else:
            change_label.setStyleSheet("color: #888888;")
        
        # Last 3 values
        last_3_values = self.data.get('last_3', [])
        if len(last_3_values) >= 3:
            if 'Treas' in self.name or 'CPI' in self.name or 'Fed' in self.name:
                last_3_text = f"{last_3_values[0]:.2f} {last_3_values[1]:.2f} {last_3_values[2]:.2f}"
            else:
                last_3_text = f"{last_3_values[0]:.1f} {last_3_values[1]:.1f} {last_3_values[2]:.1f}"
        else:
            last_3_text = "-- -- --"
            
        last_3_label = QLabel(last_3_text)
        last_3_label.setFont(QFont("Consolas", 8))
        last_3_label.setStyleSheet("color: #aaaaaa;")
        last_3_label.setFixedWidth(120)
        last_3_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # mini chart
        chart = MiniChart(self.data['values'])
        
        # date
        date_label = QLabel(self.data['date'])
        date_label.setFont(QFont("Consolas", 8))
        date_label.setStyleSheet("color: #888888;")
        date_label.setFixedWidth(70)
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # add widgets
        layout.addWidget(name_label)
        layout.addWidget(current_label)
        layout.addWidget(change_label)
        layout.addWidget(last_3_label)
        layout.addWidget(chart)
        layout.addWidget(date_label)
        layout.addStretch()
        
        self.setLayout(layout)

class EconomicDataView(QObject):
    def __init__(self, components, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.economicDataContainer = components['economicDataContainer']
        self.economicDataFooter = components['economicDataFooter']
        
        # set container background to match dashboard
        self.economicDataContainer.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
        
        self.fred = None
        self.indicators = {
            'Federal Funds Rate': 'FEDFUNDS',
            '10Y Treasury Bonds': 'GS10',
            'VIX': 'VIXCLS',
            'Unemployment': 'UNRATE',
            'CPI': 'CPIAUCSL',
            'Sentiment': 'UMCSENT',
            '2Y Treasury Bonds': 'GS2',
            'Oil WTI': 'DCOILWTICO',
            'DXY': 'DTWEXBGS'
        }
        
        # Initialize FRED API
        try:
            from fredapi import Fred
            from FRED.config import FRED_API_KEY
            self.fred = Fred(api_key=FRED_API_KEY)
        except ImportError:
            print("FRED API not available - using mock data")
        
        self.rows = []
        self.populate_economic_data()
        
    def populate_economic_data(self):
        # Clear existing rows
        layout = self.economicDataContainer.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), EconomicRow):
                item.widget().setParent(None)
        
        # Mock data for now (replace with FRED data when available)
        mock_data = {
            'Fed Funds': {'current': 5.25, 'change': 0.25, 'date': '12/15/2024', 'values': [4.50, 4.75, 5.00, 5.25, 5.25, 5.50], 'last_3': [4.75, 5.00, 5.25]},
            '10Y Treas': {'current': 4.15, 'change': -0.08, 'date': '12/16/2024', 'values': [4.31, 4.23, 4.28, 4.15, 4.12, 4.18], 'last_3': [4.23, 4.28, 4.15]},
            'VIX': {'current': 18.5, 'change': 2.3, 'date': '12/16/2024', 'values': [15.2, 16.8, 16.2, 18.5, 19.1, 17.8], 'last_3': [16.8, 16.2, 18.5]},
            'Unemploy': {'current': 3.7, 'change': 0.1, 'date': '11/30/2024', 'values': [3.5, 3.6, 3.6, 3.7, 3.7, 3.8], 'last_3': [3.6, 3.6, 3.7]},
            'CPI': {'current': 3.2, 'change': -0.1, 'date': '12/10/2024', 'values': [3.7, 3.5, 3.3, 3.2, 3.1, 3.0], 'last_3': [3.5, 3.3, 3.2]},
            'Sentiment': {'current': 71.8, 'change': 4.2, 'date': '12/13/2024', 'values': [63.9, 68.5, 67.6, 71.8, 73.2, 69.5], 'last_3': [68.5, 67.6, 71.8]}
        }
        
        # Create rows
        self.rows = []
        for name, data in mock_data.items():
            row = EconomicRow(name, data)
            self.rows.append(row)
            # Insert before the spacer
            layout.insertWidget(layout.count() - 1, row)
        
        # Update footer
        self.economicDataFooter.setText(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

class DashboardView(QMainWindow):
    #declaring type for ide
    dateLabel: QLabel
    
    
    # Chart controls
    refreshButton: QPushButton
    refreshButton2: QPushButton
    timeframeCombo: QComboBox
    timeframeCombo2: QComboBox
    
    # Top-right quad chart widgets (TR = Top Right)
    TR_TL_ChartWidget: QWebEngineView  # Top Right, Top Left (was spyChartWidget)
    TR_TR_ChartWidget: QWebEngineView  # Top Right, Top Right (was qqqChartWidget)
    TR_BL_ChartWidget: QWebEngineView  # Top Right, Bottom Left
    TR_BR_ChartWidget: QWebEngineView  # Top Right, Bottom Right
    
    # Bottom-right quad chart widgets (BR = Bottom Right)
    BR_TL_ChartWidget: QWebEngineView  # Bottom Right, Top Left
    BR_TR_ChartWidget: QWebEngineView  # Bottom Right, Top Right
    BR_BL_ChartWidget: QWebEngineView  # Bottom Right, Bottom Left
    BR_BR_ChartWidget: QWebEngineView  # Bottom Right, Bottom Right
    
    # Layout components
    holdingsFrame: QFrame
    newsFrame: QFrame
    mainSplitter: QSplitter
    leftSplitter: QSplitter
    rightSplitter: QSplitter

    holdingsTable: QTableWidget
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
    
    #economic data components
    economicDataContainer: QWidget
    economicDataFooter: QLabel


    def __init__(self):
        super().__init__()
        uic.loadUi("ui_files/dashboard_view.ui", self)
        # self.frame.hide()
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint)


        #DYNAMIC LAYOUT ADJUSTMENTS
        right_total_height = self.rightSplitter.height()
        half_height = right_total_height // 2
        self.rightSplitter.setSizes([half_height, half_height])

        left_total_height = self.leftSplitter.height()
        half_height = left_total_height // 2
        self.leftSplitter.setSizes([half_height, half_height])

        main_total_height = self.mainSplitter.height()
        half_height = main_total_height // 2
        self.mainSplitter.setSizes([half_height, half_height])
        #DYNAMIC LAYOUT ADJUSTMENTS





        chart_components = {
            # Controls for top-right quad
            'refreshButton': self.refreshButton,
            'timeframeCombo': self.timeframeCombo,
            
            # Controls for bottom-right quad  
            'refreshButton2': self.refreshButton2,
            'timeframeCombo2': self.timeframeCombo2,
            
            # Top-right quad chart widgets
            'TR_TL_ChartWidget': self.TR_TL_ChartWidget,
            'TR_TR_ChartWidget': self.TR_TR_ChartWidget,
            'TR_BL_ChartWidget': self.TR_BL_ChartWidget,
            'TR_BR_ChartWidget': self.TR_BR_ChartWidget,
            
            # Bottom-right quad chart widgets
            'BR_TL_ChartWidget': self.BR_TL_ChartWidget,
            'BR_TR_ChartWidget': self.BR_TR_ChartWidget,
            'BR_BL_ChartWidget': self.BR_BL_ChartWidget,
            'BR_BR_ChartWidget': self.BR_BR_ChartWidget
        }
        etrade_components = {
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
        
        economic_components = {
            'economicDataContainer': self.economicDataContainer,
            'economicDataFooter': self.economicDataFooter
        }

        self.ChartView = ChartView(chart_components, self)
        self.EtradeView = EtradeView(etrade_components, self)
        self.EconomicDataView = EconomicDataView(economic_components, self)
        self.date = str(QDate.currentDate().toPyDate())

        #Configure
        # self.dateLabel.setText(QDate.currentDate().toString())

class ChartView:
    def __init__(self, components, dashboard):
        super().__init__()
        self.dashboard = dashboard
        # Top-right quad controls
        self.refreshButton = components['refreshButton']
        self.timeframeCombo = components['timeframeCombo']
        
        # Bottom-right quad controls
        self.refreshButton2 = components['refreshButton2']
        self.timeframeCombo2 = components['timeframeCombo2']
        
        # Top-right quad chart widgets
        self.TR_TL_ChartWidget = components['TR_TL_ChartWidget']
        self.TR_TR_ChartWidget = components['TR_TR_ChartWidget']
        self.TR_BL_ChartWidget = components['TR_BL_ChartWidget']
        self.TR_BR_ChartWidget = components['TR_BR_ChartWidget']
        
        # Bottom-right quad chart widgets
        self.BR_TL_ChartWidget = components['BR_TL_ChartWidget']
        self.BR_TR_ChartWidget = components['BR_TR_ChartWidget']
        self.BR_BL_ChartWidget = components['BR_BL_ChartWidget']
        self.BR_BR_ChartWidget = components['BR_BR_ChartWidget']
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
        self.timeframe_input2 = ""

        self.symbol1 = None  # TR_TL
        self.symbol2 = None  # TR_TR
        self.symbol3 = None  # TR_BL
        self.symbol4 = None  # TR_BR

        self.symbol5 = None  # BR_TL
        self.symbol6 = None  # BR_TR
        self.symbol7 = None  # BR_BL
        self.symbol8 = None  # BR_BR

        self._init_graph_menu()

        #wiring
        self.refreshButton.clicked.connect(self.press_refresh_button_top)
        self.refreshButton2.clicked.connect(self.press_refresh_button_bottom)

        #load charts on instantiation
        self.press_refresh_button_top()
        self.press_refresh_button_bottom()

    def _init_graph_menu(self):
        inputs_config = [
            (self.dashboard.menuTopTL, "QQQ", "topTL_input"),
            (self.dashboard.menuTopTR, "SPY", "topTR_input"),
            (self.dashboard.menuTopBL, "NVDA", "topBL_input"), 
            (self.dashboard.menuTopBR, "AMZN", "topBR_input"),
            (self.dashboard.menuBottomTL, "HYG", "bottomTL_input"),
            (self.dashboard.menuBottomTR, "TLT", "bottomTR_input"),
            (self.dashboard.menuBottomBL, "IBIT", "bottomBL_input"),
            (self.dashboard.menuBottomBR, "GLD", "bottomBR_input")
        ]
        
        for menu, default_text, attr_name in inputs_config:
            line_edit = QLineEdit()
            line_edit.setText(default_text)
            line_edit.setPlaceholderText("Enter ticker...")
            line_edit.setMaximumWidth(100)
            
            widget_action = QWidgetAction(self.dashboard)
            widget_action.setDefaultWidget(line_edit)
            menu.addAction(widget_action)
            
            setattr(self, attr_name, line_edit)

    def chart_symbol(self, symbol, widget, timeframe_input):
        try:
            symbol_data = yf.download(symbol, period=timeframe_input, interval=self.timeframe_intervals[timeframe_input])
            symbol_closes = symbol_data[['Close']].dropna()
            symbol_closes.columns = symbol_closes.columns.droplevel('Ticker')
            
            def format_large_number(num):
                if num is None or num == 0:
                    return "N/A"
                if abs(num) >= 1e12:
                    return f"{num/1e12:.1f}T"
                elif abs(num) >= 1e9:
                    return f"{num/1e9:.1f}B"
                elif abs(num) >= 1e6:
                    return f"{num/1e6:.0f}M"
                else:
                    return f"{num:.2f}"
            
            def safe_get_info(ticker_info, key, default="N/A"):
                try:
                    value = ticker_info.get(key, default)
                    return value if value is not None else default
                except:
                    return default
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            open_price = safe_get_info(info, 'open', 0)
            day_high = safe_get_info(info, 'dayHigh', 0)
            day_low = safe_get_info(info, 'dayLow', 0)
            market_cap = safe_get_info(info, 'marketCap', 0)
            week52_low = safe_get_info(info, 'fiftyTwoWeekLow', 0)
            week52_high = safe_get_info(info, 'fiftyTwoWeekHigh', 0)
            
            modified_title = (f"{symbol} |  Open:{open_price:.2f}  High:{day_high:.2f}  Low:{day_low:.2f} "
                            f" CAP:{format_large_number(market_cap)}  52L:{week52_low:.2f}  52H:{week52_high:.2f}")
            
            fig = px.line(symbol_closes, y='Close', x=symbol_closes.index, title=modified_title)

            fig.update_layout(
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(l=0, r=0, b=0, t=35, pad=0),
                showlegend=False,
                plot_bgcolor="black",
                paper_bgcolor="black",
                title=dict(
                    font=dict(size=14)
                ),
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
                        margin: 2px;
                        padding: 0;
                        background-color: black;
                    }}
                </style>
            </head>
            <body>
                {fig.to_html(include_plotlyjs='cdn', full_html=True)}
            </body>
            </html>
            """

            widget.setHtml(html)


        except Exception as e:
            print(e)

    def press_refresh_button_top(self):
        """Handle refresh for top-right quad charts"""
        # Get symbol inputs from menu QLineEdits
        symbol1_input = self.topTL_input.text().strip().upper()
        symbol2_input = self.topTR_input.text().strip().upper()
        symbol3_input = self.topBL_input.text().strip().upper()
        symbol4_input = self.topBR_input.text().strip().upper()
        self.timeframe_input = self.timeframeCombo.currentText().strip()

        # Update symbols if provided
        if symbol1_input:
            self.symbol1 = symbol1_input
        if symbol2_input:
            self.symbol2 = symbol2_input
        if symbol3_input:
            self.symbol3 = symbol3_input
        if symbol4_input:
            self.symbol4 = symbol4_input

        # Chart all top-right quad symbols
        if self.symbol1:
            self.chart_symbol(self.symbol1, self.TR_TL_ChartWidget, self.timeframe_input)
        if self.symbol2:
            self.chart_symbol(self.symbol2, self.TR_TR_ChartWidget, self.timeframe_input)
        if self.symbol3:
            self.chart_symbol(self.symbol3, self.TR_BL_ChartWidget, self.timeframe_input)
        if self.symbol4:
            self.chart_symbol(self.symbol4, self.TR_BR_ChartWidget, self.timeframe_input)

    def press_refresh_button_bottom(self):
        """Handle refresh for bottom-right quad charts"""
        # Get symbol inputs from menu QLineEdits
        symbol5_input = self.bottomTL_input.text().strip().upper()
        symbol6_input = self.bottomTR_input.text().strip().upper()
        symbol7_input = self.bottomBL_input.text().strip().upper()
        symbol8_input = self.bottomBR_input.text().strip().upper()
        self.timeframe_input2 = self.timeframeCombo2.currentText().strip()

        # Update symbols if provided
        if symbol5_input:
            self.symbol5 = symbol5_input
        if symbol6_input:
            self.symbol6 = symbol6_input
        if symbol7_input:
            self.symbol7 = symbol7_input
        if symbol8_input:
            self.symbol8 = symbol8_input

        # Chart all bottom-right quad symbols
        if self.symbol5:
            self.chart_symbol(self.symbol5, self.BR_TL_ChartWidget, self.timeframe_input2)
        if self.symbol6:
            self.chart_symbol(self.symbol6, self.BR_TR_ChartWidget, self.timeframe_input2)
        if self.symbol7:
            self.chart_symbol(self.symbol7, self.BR_BL_ChartWidget, self.timeframe_input2)
        if self.symbol8:
            self.chart_symbol(self.symbol8, self.BR_BR_ChartWidget, self.timeframe_input2)

class EtradeView(QObject):
    viewModeGroup: QActionGroup
    accountSelectMenu: QMenu
    accountActionGroup: QActionGroup
    def __init__(self, components, dashboard):
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

        self.dashboard = dashboard
        self.holdingsTable = components['holdingsTable']
        self.actionSimple = components['actionSimple']
        self.actionDynamic = components['actionDynamic']
        self.actionFull = components['actionFull']
        self.actionCustom = components['actionCustom']
        self.viewModeGroup = QActionGroup(self)

        #holdingsTable settings
        self.holdingsTable.horizontalHeader().setStretchLastSection(True)
        self.holdingsTable.verticalHeader().setVisible(False)

        self.pollingrate = 10
        self.session, self.base_url = oauth()
        self.accounts_manager = AccountsManager(self.session, self.base_url)
        self.current_account_index = None
        self._threads, self._workers = [], []
        self._init_accounts_menu()
        self._init_action_group()
        self.populate_portfolio_table()
        self.populate_accounttables_footer()
        self.startPolling()

    def startPolling(self):
        self._start_one(
            lambda: self.accounts_manager.fetch_balances(
            self.accounts_manager.accounts_list[self.current_account_index].accountIdKey, 
            self.accounts_manager.accounts_list[self.current_account_index].institutionType
            ), self.populate_accounttables_footer, self.pollingrate)
        
        self._start_one(
            lambda: self.accounts_manager.fetch_portfolio(
            self.accounts_manager.accounts_list[self.current_account_index].accountIdKey
            ), self.populate_portfolio_table, self.pollingrate)


    def _start_one(self,fetch_fn,slot,interval):
        worker = PollWorker(fetch_fn, interval)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        worker.dataReady.connect(slot)
        worker.finished.connect(thread.quit)
        self._threads.append(thread); self._workers.append(worker)
        thread.start()

    def stopPolling(self):
        for thread, worker in zip(self._threads, self._workers):
            worker.stop()
            thread.quit()
        self._threads.clear(); self._workers.clear()

    def _init_accounts_menu(self):
        self.accountSelectMenu = self.dashboard.menuSelectAccount
        self.accountActionGroup = QActionGroup(self)
        self.accountActionGroup.setExclusive(True)
        
        for account_index, account in enumerate(self.accounts_manager.accounts_list):
            action_text = account.account_info.get('accountDesc') + " - " + str(account.account_info.get('accountId'))
            action = QAction(action_text, self)
            action.setCheckable(True)
            action.setData(account_index)
            self.accountActionGroup.addAction(action)
            self.accountSelectMenu.addAction(action)
        
        start_index = self.accounts_manager.num_of_accounts - 1
        self.current_account_index = start_index
        self.accountActionGroup.actions()[start_index].setChecked(True)
        self.accountActionGroup.triggered.connect(self._on_account_select_changed)

    def _init_action_group(self):
        self.viewModeGroup.setExclusive(True)
        self.viewModeGroup.addAction(self.actionSimple)
        self.viewModeGroup.addAction(self.actionDynamic)
        self.viewModeGroup.addAction(self.actionFull)
        self.viewModeGroup.addAction(self.actionCustom)
        self.viewModeGroup.triggered.connect(self._on_action_group_viewmode_change)
        self.actionDynamic.setChecked(True)

    def _on_account_select_changed(self, action):
        self.stopPolling()
        self.current_account_index = action.data()
        self.populate_portfolio_table()
        self.populate_accounttables_footer()
        self.startPolling()

    def _on_action_group_viewmode_change(self):
        self.populate_portfolio_table()

#NOTE NEED TO FINISH FORMATTING
    def populate_portfolio_table(self):
        try:
            if (self.current_account_index is None or 
                self.current_account_index >= len(self.accounts_manager.accounts_list)):
                return

            account = self.accounts_manager.accounts_list[self.current_account_index]
            if not hasattr(account, 'positions') or account.positions.empty:
                self.holdingsTable.clear()
                self.holdingsTable.setRowCount(0)
                self.holdingsTable.setColumnCount(0)
                return

            self.holdingsTable.clear()
            self.holdingsTable.setRowCount(0)
            self.holdingsTable.setColumnCount(0)

            positions_original = account.positions.copy()
            
            def _portfolio_view_select_adjust(df):
                selected_action = self.viewModeGroup.checkedAction()
                if selected_action:
                    if selected_action.objectName() == 'actionSimple' or selected_action.objectName() == 'actionDynamic':
                        required_cols = ['symbolDescription', 'lastTrade', 'change', 'quantity', 'daysGain', 'daysGainPct', 'totalGain', 'totalGainPct', 'pctOfPortfolio']
                        available_cols = [col for col in required_cols if col in df.columns]
                        df = df[available_cols]
                    elif selected_action.objectName() == 'actionFull':
                        pass
                    elif selected_action.objectName() == 'actionCustom':
                        pass
                return df

            positions_filtered = _portfolio_view_select_adjust(positions_original)
            
            def _format_data(df):
                df_copy = df.copy()
                selected_action = self.viewModeGroup.checkedAction()
                
                if selected_action and selected_action.objectName() == 'actionDynamic':
                    if 'lastTrade' in df_copy.columns and 'change' in df_copy.columns:
                        df_copy['lastTrade(d)'] = df_copy.apply(
                            lambda row: f"{row['lastTrade']:.2f} ({row['change']:+.2f})", axis=1
                        )
                        df_copy = df_copy.drop(columns=['lastTrade', 'change'], errors='ignore')

                    if 'daysGainPct' in df_copy.columns and 'daysGain' in df_copy.columns:
                        df_copy['dayChange'] = df_copy.apply(
                            lambda row: f"{row['daysGainPct']:.2f}% ({row['daysGain']:+.2f})", axis=1
                        )
                        df_copy = df_copy.drop(columns=['daysGainPct', 'daysGain'], errors='ignore')

                    cols = df_copy.columns.tolist()
                    if 'lastTrade(d)' in cols:
                        cols.insert(1, cols.pop(cols.index('lastTrade(d)')))
                    if 'dayChange' in cols:
                        cols.insert(2, cols.pop(cols.index('dayChange')))
                    df_copy = df_copy[cols]

                return df_copy

            final_data = _format_data(positions_filtered).reset_index(drop=True)

            def _check_if_colored(item, col_name, value):
                if 'Pct' in col_name or 'Gain' in col_name or 'change' in col_name:
                    if isinstance(value, (int, float, complex)):
                        if value > 0:
                            item.setForeground(QBrush(QColor('green')))
                        elif value < 0:
                            item.setForeground(QBrush(QColor('red')))
                elif col_name in ['lastTrade(d)', 'dayChange']:
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

            self.holdingsTable.setRowCount(len(final_data))
            self.holdingsTable.setColumnCount(len(final_data.columns))
            self.holdingsTable.setHorizontalHeaderLabels(final_data.columns.tolist())
            
            for i in range(len(final_data)):
                for j in range(len(final_data.columns)):
                    value = final_data.iloc[i, j]
                    item = QTableWidgetItem(str(value))
                    col_name = final_data.columns[j]
                    _check_if_colored(item, col_name, value)
                    self.holdingsTable.setItem(i, j, item)

            self.holdingsTable.resizeColumnsToContents()

        except Exception as e:
            print(f"Error populating portfolio table: {e}")
            self.holdingsTable.clear()
            self.holdingsTable.setRowCount(0)
            self.holdingsTable.setColumnCount(0)

    def populate_accounttables_footer(self):

        def _format_gain_loss_label(label, value):
            base_style = "background-color: transparent; border: none; font-size: 14px;"
            if value > 0:
                label.setStyleSheet(base_style + "color: green;")
            elif value < 0:
                label.setStyleSheet(base_style + "color: red;")
            else:
                label.setStyleSheet(base_style)

        def _safe_get_value(df, key, default=0.0):
            try:
                return df.loc[key]
            except (KeyError, IndexError):
                return default

        accounttotals = self.accounts_manager.accounts_list[self.current_account_index].accounttotals.copy()
        balances = self.accounts_manager.accounts_list[self.current_account_index].balances.copy()

        # Set text and apply color formatting for gain/loss labels
        todays_gain_loss = _safe_get_value(accounttotals, 'todaysGainLoss')
        todays_gain_loss_pct = _safe_get_value(accounttotals, 'todaysGainLossPct')
        total_gain_loss = _safe_get_value(accounttotals, 'totalGainLoss')
        total_gain_loss_pct = _safe_get_value(accounttotals, 'totalGainLossPct')

        self.todaysGainLossLabel.setText(f"${todays_gain_loss:.2f}")
        _format_gain_loss_label(self.todaysGainLossLabel, todays_gain_loss)
        
        self.todaysGainLossPctLabel.setText(f"{todays_gain_loss_pct:.2f}%")
        _format_gain_loss_label(self.todaysGainLossPctLabel, todays_gain_loss_pct)
        
        self.totalGainLossLabel.setText(f"${total_gain_loss:.2f}")
        _format_gain_loss_label(self.totalGainLossLabel, total_gain_loss)
        
        self.totalGainLossPctLabel.setText(f"{total_gain_loss_pct:.2f}%")
        _format_gain_loss_label(self.totalGainLossPctLabel, total_gain_loss_pct)

        # These labels remain unformatted
        total_market_value = _safe_get_value(accounttotals, 'totalMarketValue')
        cash_balance = _safe_get_value(accounttotals, 'cashBalance')
        
        self.totalMarketValueLabel.setText(f"${total_market_value:.2f}")
        self.cashBalanceLabel.setText(f"${cash_balance:.2f}")

        self.nonMarginableSecuritiesPPLabel.setText(f"${_safe_get_value(balances, 'netCash'):.2f}")
        self.netAccountValueLabel.setText(f"${total_market_value + cash_balance:.2f}")
        self.marginableSecuritiesPPLabel.setText(f"${_safe_get_value(balances, 'marginBuyingPower'):.2f}")
        self.marginLabel.setText(f"${_safe_get_value(balances, 'marginBalance'):.2f}")
        self.cashInvestableLabel.setText(f"${_safe_get_value(balances, 'cashAvailableForInvestment'):.2f}")
        
        total_assets = self.accounts_manager.calculate_total_assets_across_accounts()
        self.totalAssetsLabel.setText(f"${total_assets:.2f}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardView()
    window.show()
    sys.exit(app.exec())



