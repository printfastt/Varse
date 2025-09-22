from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class ResearchTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Research")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()
        label = QLabel("Hello! This is the research tab.")
        layout.addWidget(label)
        self.setLayout(layout)
