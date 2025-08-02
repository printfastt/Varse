"""
Enhanced Price Chart Widget with comprehensive charting capabilities
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Optional, List, Any
import numpy as np


class PriceChartRenderer:
    """
    Advanced price chart renderer with support for:
    - Multiple chart types (Line, Candlestick, OHLC, Area)
    - Technical indicators overlay
    - Volume charts
    - Comparison mode
    - Customizable styling
    """
    
    def __init__(self):
        self.theme_colors = {
            'background': 'rgba(10, 10, 10, 0.9)',
            'paper': 'rgba(15, 15, 25, 0.9)',
            'grid': 'rgba(255, 255, 255, 0.1)',
            'text': '#ffffff',
            'line_primary': '#00ffff',
            'line_secondary': '#ff6b9d',
            'line_accent': '#c77dff',
            'volume': 'rgba(0, 255, 255, 0.3)',
            'green': '#00ff88',
            'red': '#ff4757',
            'yellow': '#fffa65',
        }
    
    def create_chart(self, data: pd.DataFrame, symbol: str, chart_type: str = 'line',
                    indicators: Optional[Dict] = None, show_volume: bool = False,
                    comparison_data: Optional[pd.DataFrame] = None, 
                    comparison_symbol: Optional[str] = None) -> str:
        """
        Create comprehensive stock chart
        
        Args:
            data: OHLCV DataFrame
            symbol: Stock symbol
            chart_type: 'line', 'candlestick', 'ohlc', 'area'
            indicators: Dictionary of technical indicators
            show_volume: Whether to show volume subplot
            comparison_data: Data for comparison chart
            comparison_symbol: Symbol for comparison
            
        Returns:
            HTML string for the chart
        """
        if data.empty:
            return self._create_error_chart("No data available")
        
        try:
            # Determine number of subplots
            subplot_count = 1
            subplot_titles = [f"{symbol} - {chart_type.title()} Chart"]
            
            if show_volume:
                subplot_count += 1
                subplot_titles.append("Volume")
            
            # Create subplots
            fig = make_subplots(
                rows=subplot_count,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=subplot_titles,
                row_width=[0.7, 0.3] if show_volume else [1.0]
            )
            
            # Add main price chart
            self._add_price_chart(fig, data, symbol, chart_type, row=1)
            
            # Add technical indicators
            if indicators:
                self._add_technical_indicators(fig, data, indicators, row=1)
            
            # Add comparison chart
            if comparison_data is not None and comparison_symbol:
                self._add_comparison_chart(fig, comparison_data, comparison_symbol, row=1)
            
            # Add volume chart
            if show_volume:
                self._add_volume_chart(fig, data, row=subplot_count)
            
            # Update layout
            self._update_layout(fig, data, symbol)
            
            return self._wrap_chart_html(fig)
            
        except Exception as e:
            print(f"Error creating chart: {e}")
            return self._create_error_chart(f"Error creating chart: {str(e)}")
    
    def _add_price_chart(self, fig: go.Figure, data: pd.DataFrame, symbol: str, 
                        chart_type: str, row: int = 1):
        """Add main price chart based on type"""
        
        if chart_type == 'candlestick':
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    name=symbol,
                    increasing_line_color=self.theme_colors['green'],
                    decreasing_line_color=self.theme_colors['red'],
                    increasing_fillcolor=self.theme_colors['green'],
                    decreasing_fillcolor=self.theme_colors['red']
                ),
                row=row, col=1
            )
        
        elif chart_type == 'ohlc':
            fig.add_trace(
                go.Ohlc(
                    x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    name=symbol,
                    increasing_line_color=self.theme_colors['green'],
                    decreasing_line_color=self.theme_colors['red']
                ),
                row=row, col=1
            )
        
        elif chart_type == 'area':
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Close'],
                    mode='lines',
                    name=symbol,
                    line=dict(color=self.theme_colors['line_primary'], width=2),
                    fill='tonexty',
                    fillcolor='rgba(0, 255, 255, 0.1)'
                ),
                row=row, col=1
            )
        
        else:  # line chart
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Close'],
                    mode='lines',
                    name=symbol,
                    line=dict(color=self.theme_colors['line_primary'], width=3)
                ),
                row=row, col=1
            )
    
    def _add_technical_indicators(self, fig: go.Figure, data: pd.DataFrame, 
                                 indicators: Dict, row: int = 1):
        """Add technical indicators to the chart"""
        
        for indicator_name, indicator_data in indicators.items():
            if indicator_data is None or indicator_data.empty:
                continue
                
            # Moving Averages
            if 'SMA' in indicator_name or 'EMA' in indicator_name:
                color = self.theme_colors['line_secondary'] if 'SMA' in indicator_name else self.theme_colors['line_accent']
                fig.add_trace(
                    go.Scatter(
                        x=indicator_data.index,
                        y=indicator_data,
                        mode='lines',
                        name=indicator_name,
                        line=dict(color=color, width=2, dash='dot'),
                        opacity=0.8
                    ),
                    row=row, col=1
                )
            
            # Bollinger Bands
            elif 'BB_Upper' in indicator_name:
                # Add upper band
                fig.add_trace(
                    go.Scatter(
                        x=indicator_data.index,
                        y=indicator_data,
                        mode='lines',
                        name='BB Upper',
                        line=dict(color=self.theme_colors['yellow'], width=1),
                        opacity=0.6
                    ),
                    row=row, col=1
                )
                
            elif 'BB_Lower' in indicator_name:
                # Add lower band with fill
                fig.add_trace(
                    go.Scatter(
                        x=indicator_data.index,
                        y=indicator_data,
                        mode='lines',
                        name='BB Lower',
                        line=dict(color=self.theme_colors['yellow'], width=1),
                        fill='tonexty',
                        fillcolor='rgba(255, 250, 101, 0.1)',
                        opacity=0.6
                    ),
                    row=row, col=1
                )
            
            elif 'BB_Middle' in indicator_name:
                fig.add_trace(
                    go.Scatter(
                        x=indicator_data.index,
                        y=indicator_data,
                        mode='lines',
                        name='BB Middle',
                        line=dict(color=self.theme_colors['yellow'], width=1, dash='dash'),
                        opacity=0.7
                    ),
                    row=row, col=1
                )
    
    def _add_comparison_chart(self, fig: go.Figure, comparison_data: pd.DataFrame,
                            comparison_symbol: str, row: int = 1):
        """Add comparison chart (normalized to percentage change)"""
        if not comparison_data.empty and 'Close' in comparison_data.columns:
            # Normalize to percentage change from first value
            normalized_data = (comparison_data['Close'] / comparison_data['Close'].iloc[0] - 1) * 100
            
            fig.add_trace(
                go.Scatter(
                    x=comparison_data.index,
                    y=normalized_data,
                    mode='lines',
                    name=f"{comparison_symbol} (%)",
                    line=dict(color=self.theme_colors['line_secondary'], width=2),
                    yaxis='y2'  # Use secondary y-axis
                ),
                row=row, col=1
            )
    
    def _add_volume_chart(self, fig: go.Figure, data: pd.DataFrame, row: int = 2):
        """Add volume chart as subplot"""
        if 'Volume' in data.columns:
            # Color bars based on price movement
            colors = []
            for i in range(len(data)):
                if i == 0 or data['Close'].iloc[i] >= data['Close'].iloc[i-1]:
                    colors.append(self.theme_colors['green'])
                else:
                    colors.append(self.theme_colors['red'])
            
            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['Volume'],
                    name='Volume',
                    marker_color=colors,
                    opacity=0.7
                ),
                row=row, col=1
            )
    
    def _update_layout(self, fig: go.Figure, data: pd.DataFrame, symbol: str):
        """Update chart layout with theme and styling"""
        
        # Calculate price change for title
        if len(data) > 1:
            current_price = data['Close'].iloc[-1]
            previous_price = data['Close'].iloc[-2]
            change = current_price - previous_price
            change_pct = (change / previous_price) * 100 if previous_price != 0 else 0
            
            title_color = self.theme_colors['green'] if change >= 0 else self.theme_colors['red']
            title = (f"{symbol} - ${current_price:.2f} "
                    f"({change:+.2f}, {change_pct:+.2f}%)")
        else:
            title = f"{symbol} Stock Chart"
            title_color = self.theme_colors['text']
        
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(color=title_color, size=16),
                x=0.5,
                xanchor='center'
            ),
            plot_bgcolor=self.theme_colors['background'],
            paper_bgcolor=self.theme_colors['paper'],
            font=dict(color=self.theme_colors['text'], family='Consolas, monospace'),
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(0,0,0,0.5)',
                bordercolor=self.theme_colors['grid'],
                borderwidth=1,
                x=0.02,
                y=0.98
            ),
            hovermode='x unified',
            dragmode='zoom'
        )
        
        # Update axes
        fig.update_xaxes(
            showgrid=True,
            gridcolor=self.theme_colors['grid'],
            gridwidth=1,
            showline=True,
            linecolor=self.theme_colors['grid'],
            mirror=True
        )
        
        fig.update_yaxes(
            showgrid=True,
            gridcolor=self.theme_colors['grid'],
            gridwidth=1,
            showline=True,
            linecolor=self.theme_colors['grid'],
            mirror=True,
            fixedrange=False
        )
        
        # Remove range slider and add custom rangeslider
        fig.update_layout(xaxis_rangeslider_visible=False)
    
    def _wrap_chart_html(self, fig: go.Figure) -> str:
        """Wrap chart in HTML with custom styling"""
        chart_html = fig.to_html(include_plotlyjs='cdn', full_html=False, config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d', 'autoScale2d'],
            'responsive': True
        })
        
        return f"""
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 5px;
                    background-color: {self.theme_colors['background']};
                    font-family: 'Consolas', 'JetBrains Mono', monospace;
                }}
                .modebar {{
                    background-color: rgba(25, 25, 35, 0.8) !important;
                }}
                .modebar-btn {{
                    color: {self.theme_colors['text']} !important;
                }}
                .modebar-btn:hover {{
                    background-color: rgba(0, 255, 255, 0.2) !important;
                }}
            </style>
        </head>
        <body>
            {chart_html}
        </body>
        </html>
        """
    
    def _create_error_chart(self, error_message: str) -> str:
        """Create error chart when data is unavailable"""
        return f"""
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    background-color: {self.theme_colors['background']};
                    color: {self.theme_colors['text']};
                    font-family: 'Consolas', 'JetBrains Mono', monospace;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    text-align: center;
                }}
                .error-message {{
                    font-size: 14px;
                    color: {self.theme_colors['red']};
                }}
            </style>
        </head>
        <body>
            <div class="error-message">
                {error_message}
            </div>
        </body>
        </html>
        """


# Global instance
chart_renderer = PriceChartRenderer()
