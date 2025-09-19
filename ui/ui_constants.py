"""
UI Constants for standardized formatting across the application.
Contains fonts, colors, sizes, and common style patterns.
"""

from PyQt6.QtGui import QFont, QColor

# ===============================
# FONT CONSTANTS
# ===============================

class FontFamily:
    PRIMARY = "Consolas"

class FontSize:
    TINY = 8
    SMALL = 9  
    MEDIUM = 10
    LARGE = 14

class FontWeight:
    NORMAL = QFont.Weight.Normal
    BOLD = QFont.Weight.Bold

# Pre-defined font combinations for common use cases
class StandardFonts:
    TINY = QFont(FontFamily.PRIMARY, FontSize.TINY)
    SMALL = QFont(FontFamily.PRIMARY, FontSize.SMALL)
    MEDIUM = QFont(FontFamily.PRIMARY, FontSize.MEDIUM)
    LARGE = QFont(FontFamily.PRIMARY, FontSize.LARGE)
    
    TINY_BOLD = QFont(FontFamily.PRIMARY, FontSize.TINY, FontWeight.BOLD)
    SMALL_BOLD = QFont(FontFamily.PRIMARY, FontSize.SMALL, FontWeight.BOLD)
    MEDIUM_BOLD = QFont(FontFamily.PRIMARY, FontSize.MEDIUM, FontWeight.BOLD)
    LARGE_BOLD = QFont(FontFamily.PRIMARY, FontSize.LARGE, FontWeight.BOLD)

# ===============================
# COLOR CONSTANTS
# ===============================

class Colors:
    # Gain/Loss colors
    GAIN_COLOR = QColor('green')
    LOSS_COLOR = QColor('red')
    NEUTRAL_COLOR = QColor('#888888')
    
    # Text colors
    PRIMARY_TEXT = '#e0e0e0'
    SECONDARY_TEXT = '#aaaaaa'
    TERTIARY_TEXT = '#888888'
    
    # Background colors
    DARK_BACKGROUND = '#1e1e1e'
    BLACK_BACKGROUND = 'black'
    TRANSPARENT_BACKGROUND = 'transparent'
    
    # Chart colors
    CHART_LINE_PRIMARY = '#4a90e2'
    CHART_LINE_SECONDARY = 'blue'
    CHART_GRID = 'rgba(255, 255, 255, 0.1)'

# Color strings for direct use in stylesheets
class ColorStrings:
    GAIN = 'green'
    LOSS = 'red'
    NEUTRAL = '#888888'

# ===============================
# STYLE CONSTANTS
# ===============================

class StyleSheets:
    TRANSPARENT_LABEL_BASE = "background-color: transparent; border: none;"
    
    ECONOMIC_FRAME = """
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
    """
    
    @staticmethod
    def get_gain_loss_label_style(font_size: int) -> str:
        """Returns base style for gain/loss labels with specified font size"""
        return f"background-color: transparent; border: none; font-size: {font_size}px;"
    
    @staticmethod
    def get_colored_label_style(font_size: int, color: str) -> str:
        """Returns colored label style with specified font size and color"""
        base = StyleSheets.get_gain_loss_label_style(font_size)
        return base + f" color: {color};"

# ===============================
# LAYOUT CONSTANTS
# ===============================

class Layout:
    # Common margins and spacing
    TIGHT_MARGIN = 2
    STANDARD_MARGIN = 5
    WIDE_MARGIN = 10
    
    # Common widget sizes
    MINI_CHART_WIDTH = 60
    MINI_CHART_HEIGHT = 20
    
    # Common fixed widths
    NAME_LABEL_WIDTH = 100
    VALUE_LABEL_WIDTH = 60
    CHANGE_LABEL_WIDTH = 50
    LAST_VALUES_WIDTH = 120
    DATE_LABEL_WIDTH = 70
    TICKER_INPUT_WIDTH = 100

# ===============================
# CHART CONSTANTS
# ===============================

class ChartStyle:
    PLOT_BACKGROUND = "black"
    PAPER_BACKGROUND = "black"
    GRID_COLOR = 'rgba(255, 255, 255, 0.1)'
    LINE_COLOR = 'blue'
    LINE_WIDTH = 3
    TITLE_FONT_SIZE = 14
    BODY_MARGIN = dict(l=0, r=0, b=0, t=35, pad=0)
    MINI_CHART_MARGIN = 1

# ===============================
# UTILITY FUNCTIONS
# ===============================

def apply_gain_loss_color(widget, value: float):
    """Apply standard gain/loss coloring to a widget based on value"""
    base_style = StyleSheets.TRANSPARENT_LABEL_BASE + f" font-size: {FontSize.LARGE}px;"
    
    if value > 0:
        widget.setStyleSheet(base_style + f" color: {ColorStrings.GAIN};")
    elif value < 0:
        widget.setStyleSheet(base_style + f" color: {ColorStrings.LOSS};")
    else:
        widget.setStyleSheet(base_style + f" color: {ColorStrings.NEUTRAL};")

def get_gain_loss_brush(value: float):
    """Return appropriate QBrush color for gain/loss value"""
    from PyQt6.QtGui import QBrush
    
    if value > 0:
        return QBrush(Colors.GAIN_COLOR)
    elif value < 0:
        return QBrush(Colors.LOSS_COLOR)
    else:
        return QBrush(Colors.NEUTRAL_COLOR)
