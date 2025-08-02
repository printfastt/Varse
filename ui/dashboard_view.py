import sys
import yfinance as yf
from PyQt6.QtCore import QDate
from PyQt6.QtSensors import QPressureReading
from PyQt6.QtWidgets import QWidget, QLineEdit, QPushButton, QApplication, QMainWindow, QLabel
from PyQt6 import uic
import pandas as pd
import plotly.express as px
from PyQt6.QtWebEngineWidgets import QWebEngineView
from matplotlib.pyplot import xlabel


class DashboardView(QMainWindow):
    symbol1Input: QLineEdit
    symbol2Input: QLineEdit
    refreshButton: QPushButton
    qqqChartWidget: QWebEngineView
    spyChartWidget: QWebEngineView
    dateLabel: QLabel

    def __init__(self):
        super().__init__()
        uic.loadUi("ui_files/dashboard_view.ui", self)


        self.date = str(QDate.currentDate().toPyDate())
        self.symbol1 = None
        self.symbol2 = None
        self.pressRefreshButton()

        #Configure buttons
        self.dateLabel.setText(QDate.currentDate().toString())
        self.refreshButton.clicked.connect(self.pressRefreshButton)


    def pressRefreshButton(self):
        symbol1_input = self.symbol1Input.text().strip().upper()
        symbol2_input = self.symbol2Input.text().strip().upper()

        if symbol1_input is not None:
            self.symbol1 = symbol1_input
        if symbol2_input is not None:
            self.symbol2 = symbol2_input

        self.chartSymbol(self.symbol1, self.symbol2)


    def chartSymbol(self, symbol1, symbol2):
        try:
            symbol1_data = yf.download(symbol1, period="1d", interval="1m")
            symbol2_data = yf.download(symbol2, period="1d", interval="1m")
            symbol1_closes = symbol1_data[['Close']]
            symbol2_closes = symbol2_data[['Close']]
            symbol1_closes.columns = symbol1_closes.columns.droplevel('Ticker')
            symbol2_closes.columns = symbol2_closes.columns.droplevel('Ticker')
            fig1 = px.line(symbol1_closes, y='Close', x=symbol1_closes.index, title=symbol1)
            fig2 = px.line(symbol2_closes, y='Close', x=symbol2_closes.index, title=symbol2)

            fig1.update_layout(
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(l=0, r=0, b=0, t=30, pad=0),
                showlegend=False,
                plot_bgcolor="black",
                paper_bgcolor="black",
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.1)'
                ),
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.1)',
                # showticklabels=False,
                    title=None
                )
            )
            fig2.update_layout(
                xaxis_title=None,
                yaxis_title = None,
                margin=dict(l=0, r=0, b=0, t=30, pad=0),
                showlegend=False,
                plot_bgcolor="black",
                paper_bgcolor="black",
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.1)'
                ),
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    # showticklabels=False,
                    title=None
                )

            )

            fig1.update_traces(line=dict(color='blue', width=3))
            fig2.update_traces(line=dict(color='blue', width=3))
            html1 = f"""
            <html>
            <head>
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        background-color: black;
                    }}
                </style>
            </head>
            <body>
                {fig1.to_html(include_plotlyjs='cdn', full_html=False)}
            </body>
            </html>
            """

            html2 = f"""
            <html>
            <head>
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        background-color: black;
                    }}
                </style>
            </head>
            <body>
                {fig2.to_html(include_plotlyjs='cdn', full_html=False)}
            </body>
            </html>
            """

            self.spyChartWidget.setHtml(html1)
            self.qqqChartWidget.setHtml(html2)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardView()
    window.show()
    sys.exit(app.exec())


