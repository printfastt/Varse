import sys
import os
import yfinance as yf
from PyQt6.QtCore import QDate, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QLineEdit, QPushButton, QApplication, 
                            QMainWindow, QLabel, QComboBox, QTextEdit)
from PyQt6 import uic
import pandas as pd
import plotly.express as px
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_providers.yahoo_finance import yahoo_provider
from ui.widgets.price_chart import chart_renderer


class StockDataWorker(QThread):
    """Worker thread for fetching stock data without blocking UI"""
    data_ready = pyqtSignal(str, dict, pd.DataFrame)  # symbol, info, data
    error_occurred = pyqtSignal(str, str)  # symbol, error_message
    
    def __init__(self, symbol: str, period: str, interval: str):
        super().__init__()
        self.symbol = symbol
        self.period = period
        self.interval = interval
    
    def run(self):
        try:
            # Fetch stock info and data
            stock_info = yahoo_provider.get_stock_info(self.symbol)
            stock_data = yahoo_provider.get_stock_data(self.symbol, self.period, self.interval)
            self.data_ready.emit(self.symbol, stock_info, stock_data)
        except Exception as e:
            self.error_occurred.emit(self.symbol, str(e))


class DashboardView(QMainWindow):
    # Type hints for IDE
    dateLabel: QLabel
    symbol1Input: QLineEdit
    symbol2Input: QLineEdit
    refreshButton: QPushButton
    qqqChartWidget: QWebEngineView
    spyChartWidget: QWebEngineView
    timeframeCombo: QComboBox
    chartTypeCombo: QComboBox
    movingAvgCombo: QComboBox
    technicalCombo: QComboBox
    showVolumeBtn: QPushButton
    compareBtn: QPushButton
    
    # Stock info panel widgets
    symbolDisplayLabel: QLabel
    currentPriceLabel: QLabel
    priceChangeLabel: QLabel
    marketCapLabel: QLabel
    peRatioLabel: QLabel
    week52HighLabel: QLabel
    week52LowLabel: QLabel
    volumeLabel: QLabel
    avgVolumeLabel: QLabel
    dividendYieldLabel: QLabel
    epsLabel: QLabel
    companyNameLabel: QLabel
    companyDescText: QTextEdit

    def __init__(self):
        super().__init__()
        uic.loadUi("ui_files/dashboard_view.ui", self)

        # Set splitter proportions
        total_height = self.chartsSplitter.height()
        half_height = total_height // 2
        self.chartsSplitter.setSizes([half_height, half_height])
        
        # Set right splitter proportions (charts vs stock info)
        self.rightSplitter.setSizes([700, 300])

        # Current date
        self.date = str(QDate.currentDate().toPyDate())
        self.dateLabel.setText(QDate.currentDate().toString())
        
        # Stock data storage
        self.current_stock_data = {}
        self.current_stock_info = {}
        
        # Worker threads
        self.workers = {}
        
        # Initialize chart view (after workers dict is created)
        self.chart_view = EnhancedChartView(parent=self)
        
        # Auto-refresh timer (optional)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.chart_view.auto_refresh)
        # self.refresh_timer.start(60000)  # Refresh every minute (disabled by default)



class EnhancedChartView:
    """Enhanced chart view with comprehensive features"""
    
    def __init__(self, parent: DashboardView):
        self.parent: DashboardView = parent
        
        # Timeframe to interval mapping
        self.timeframe_intervals = {
            "1d": "5m",
            "5d": "15m",
            "1mo": "1h",
            "3mo": "1d",
            "1y": "1d",
            "2y": "1wk",
            "5y": "1wk",
            "max": "1wk",
        }
        
        # Connect all controls
        self._connect_controls()
        
        # Load initial charts
        self.refresh_charts()
    
    def _connect_controls(self):
        """Connect all UI controls to their handlers"""
        self.parent.refreshButton.clicked.connect(self.refresh_charts)
        self.parent.symbol1Input.returnPressed.connect(self.refresh_charts)
        self.parent.symbol2Input.returnPressed.connect(self.refresh_charts)
        self.parent.timeframeCombo.currentTextChanged.connect(self.refresh_charts)
        self.parent.chartTypeCombo.currentTextChanged.connect(self.refresh_charts)
        self.parent.movingAvgCombo.currentTextChanged.connect(self.refresh_charts)
        self.parent.technicalCombo.currentTextChanged.connect(self.refresh_charts)
        self.parent.showVolumeBtn.toggled.connect(self.refresh_charts)
        self.parent.compareBtn.toggled.connect(self.refresh_charts)
    
    def refresh_charts(self):
        """Refresh both charts with current settings"""
        symbol1 = self.parent.symbol1Input.text().strip().upper()
        symbol2 = self.parent.symbol2Input.text().strip().upper()
        
        if symbol1:
            self._fetch_and_chart_symbol(symbol1, self.parent.spyChartWidget, is_primary=True)
        
        if symbol2 and not self.parent.compareBtn.isChecked():
            self._fetch_and_chart_symbol(symbol2, self.parent.qqqChartWidget, is_primary=False)
        elif symbol2 and self.parent.compareBtn.isChecked():
            # In comparison mode, chart symbol2 on the same chart as symbol1
            self._fetch_and_chart_symbol(symbol2, self.parent.spyChartWidget, is_primary=False, is_comparison=True)
    
    def _fetch_and_chart_symbol(self, symbol: str, widget: QWebEngineView, 
                               is_primary: bool = True, is_comparison: bool = False):
        """Fetch data for a symbol and create chart"""
        timeframe = self.parent.timeframeCombo.currentText()
        interval = self.timeframe_intervals.get(timeframe, "1d")
        
        # Create and start worker thread
        worker = StockDataWorker(symbol, timeframe, interval)
        worker.data_ready.connect(
            lambda sym, info, data: self._on_data_ready(
                sym, info, data, widget, is_primary, is_comparison
            )
        )
        worker.error_occurred.connect(self._on_error)
        
        # Store worker reference and start
        self.parent.workers[symbol] = worker
        worker.start()
    
    def _on_data_ready(self, symbol: str, stock_info: dict, stock_data: pd.DataFrame,
                      widget: QWebEngineView, is_primary: bool, is_comparison: bool):
        """Handle data when ready from worker thread"""
        try:
            # Store data
            self.parent.current_stock_data[symbol] = stock_data
            self.parent.current_stock_info[symbol] = stock_info
            
            # Update stock info panel if this is the primary symbol
            if is_primary and not is_comparison:
                self._update_stock_info_panel(stock_info)
            
            # Create chart
            self._create_enhanced_chart(symbol, stock_data, widget, is_comparison)
            
        except Exception as e:
            self._show_error_chart(widget, f"Error processing data for {symbol}: {str(e)}")
    
    def _on_error(self, symbol: str, error_message: str):
        """Handle errors from worker threads"""
        print(f"Error fetching data for {symbol}: {error_message}")
        # Could show error in UI here
    
    def _create_enhanced_chart(self, symbol: str, data: pd.DataFrame, 
                             widget: QWebEngineView, is_comparison: bool = False):
        """Create enhanced chart with all features"""
        if data.empty:
            self._show_error_chart(widget, f"No data available for {symbol}")
            return
        
        try:
            # Get chart settings
            chart_type = self.parent.chartTypeCombo.currentText().lower()
            show_volume = self.parent.showVolumeBtn.isChecked()
            
            # Calculate technical indicators
            indicators = {}
            moving_avg_setting = self.parent.movingAvgCombo.currentText()
            technical_setting = self.parent.technicalCombo.currentText()
            
            # Add selected indicators
            all_indicators = yahoo_provider.calculate_technical_indicators(data)
            
            if moving_avg_setting != "None":
                if "SMA" in moving_avg_setting:
                    period = int(moving_avg_setting.split()[-1])
                    indicators[f'SMA_{period}'] = all_indicators.get(f'SMA_{period}')
                elif "EMA" in moving_avg_setting:
                    period = int(moving_avg_setting.split()[-1])
                    indicators[f'EMA_{period}'] = all_indicators.get(f'EMA_{period}')
            
            if technical_setting != "None":
                if technical_setting == "RSI":
                    indicators['RSI'] = all_indicators.get('RSI')
                elif technical_setting == "MACD":
                    indicators.update({
                        'MACD': all_indicators.get('MACD'),
                        'MACD_Signal': all_indicators.get('MACD_Signal')
                    })
                elif technical_setting == "Bollinger":
                    indicators.update({
                        'BB_Upper': all_indicators.get('BB_Upper'),
                        'BB_Middle': all_indicators.get('BB_Middle'),
                        'BB_Lower': all_indicators.get('BB_Lower')
                    })
                elif technical_setting == "Stochastic":
                    indicators.update({
                        'Stoch_K': all_indicators.get('Stoch_K'),
                        'Stoch_D': all_indicators.get('Stoch_D')
                    })
            
            # Handle comparison mode
            comparison_data = None
            comparison_symbol = None
            if is_comparison:
                comparison_data = data
                comparison_symbol = symbol
                # Get primary symbol data for main chart
                primary_symbol = self.parent.symbol1Input.text().strip().upper()
                if primary_symbol in self.parent.current_stock_data:
                    data = self.parent.current_stock_data[primary_symbol]
                    symbol = primary_symbol
            
            # Create chart
            chart_html = chart_renderer.create_chart(
                data=data,
                symbol=symbol,
                chart_type=chart_type,
                indicators=indicators,
                show_volume=show_volume,
                comparison_data=comparison_data,
                comparison_symbol=comparison_symbol
            )
            
            widget.setHtml(chart_html)
            
        except Exception as e:
            print(f"Error creating chart for {symbol}: {e}")
            self._show_error_chart(widget, f"Error creating chart: {str(e)}")
    
    def _update_stock_info_panel(self, stock_info: dict):
        """Update the stock information panel with current data"""
        try:
            # Update basic info
            self.parent.symbolDisplayLabel.setText(stock_info.get('symbol', ''))
            self.parent.companyNameLabel.setText(stock_info.get('company_name', ''))
            
            # Update price info
            current_price = stock_info.get('current_price', 0)
            change = stock_info.get('change', 0)
            change_percent = stock_info.get('change_percent', 0)
            
            self.parent.currentPriceLabel.setText(
                yahoo_provider.format_number(current_price, 'currency')
            )
            
            # Color code price change
            if change >= 0:
                price_color = '#00ff88'
                change_text = f"+{yahoo_provider.format_number(abs(change), 'currency')} (+{abs(change_percent):.2f}%)"
            else:
                price_color = '#ff4757'
                change_text = f"-{yahoo_provider.format_number(abs(change), 'currency')} (-{abs(change_percent):.2f}%)"
            
            self.parent.currentPriceLabel.setStyleSheet(f"QLabel {{ color: {price_color}; font-weight: bold; }}")
            self.parent.priceChangeLabel.setText(change_text)
            self.parent.priceChangeLabel.setStyleSheet(f"QLabel {{ color: {price_color}; }}")
            
            # Update key metrics
            self.parent.marketCapLabel.setText(
                yahoo_provider.format_number(stock_info.get('market_cap'), 'large_number')
            )
            self.parent.peRatioLabel.setText(
                yahoo_provider.format_number(stock_info.get('pe_ratio'), 'number')
            )
            self.parent.week52HighLabel.setText(
                yahoo_provider.format_number(stock_info.get('week_52_high'), 'currency')
            )
            self.parent.week52LowLabel.setText(
                yahoo_provider.format_number(stock_info.get('week_52_low'), 'currency')
            )
            self.parent.volumeLabel.setText(
                yahoo_provider.format_number(stock_info.get('volume'), 'volume')
            )
            self.parent.avgVolumeLabel.setText(
                yahoo_provider.format_number(stock_info.get('avg_volume'), 'volume')
            )
            
            dividend_yield = stock_info.get('dividend_yield')
            if dividend_yield:
                self.parent.dividendYieldLabel.setText(f"{dividend_yield*100:.2f}%")
            else:
                self.parent.dividendYieldLabel.setText("-")
                
            self.parent.epsLabel.setText(
                yahoo_provider.format_number(stock_info.get('eps_ttm'), 'currency')
            )
            
            # Update company description
            description = stock_info.get('description', '')
            if description:
                # Truncate long descriptions
                if len(description) > 500:
                    description = description[:500] + "..."
                self.parent.companyDescText.setText(description)
            else:
                self.parent.companyDescText.setText("No description available")
                
        except Exception as e:
            print(f"Error updating stock info panel: {e}")
    
    def _show_error_chart(self, widget: QWebEngineView, error_message: str):
        """Show error message in chart widget"""
        error_html = f"""
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    background-color: rgba(10, 10, 10, 0.9);
                    color: #ff4757;
                    font-family: 'Consolas', monospace;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div>{error_message}</div>
        </body>
        </html>
        """
        widget.setHtml(error_html)
    
    def auto_refresh(self):
        """Auto-refresh charts (called by timer)"""
        if not self.parent.workers:  # Only refresh if no workers are running
            self.refresh_charts()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardView()
    window.show()
    sys.exit(app.exec())
