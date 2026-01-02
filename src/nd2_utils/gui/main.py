"""
Main GUI application for ND2 to TIFF converter.
"""

import sys
import logging
from typing import Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QApplication
)

from .components import (
    FileSelectionWidget, DimensionSelectionWidget,
    OutputSelectionWidget, FileInfoWidget, ExportButtonWidget,
    ProgressWidget
)
from .handlers import GUIEventHandler, ND2FileHandler, TiffExportHandler
from ..config import setup_logging

# Configure logging to show debug messages
setup_logging()

logger = logging.getLogger(__name__)


class ND2ViewerApp(QMainWindow):
    """Main application window for ND2 viewer."""
    
    def __init__(self):
        super().__init__()
        self.nd2_info = {}
        self.init_ui()
        self.init_handlers()
        self.connect_signals()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("ND2 to TIFF Converter")
        self.setGeometry(100, 100, 600, 400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create components
        self.file_widget = FileSelectionWidget()
        self.progress_widget = ProgressWidget()
        
        # Tab widget for organization
        from PySide6.QtWidgets import QTabWidget
        self.tab_widget = QTabWidget()
        
        # File info tab
        self.info_widget = FileInfoWidget()
        self.tab_widget.addTab(self.info_widget, "File Info")
        
        # Export tab
        export_widget = self.create_export_tab()
        self.tab_widget.addTab(export_widget, "Export TIFF")
        
        # Add to main layout
        main_layout.addWidget(self.file_widget)
        main_layout.addWidget(self.progress_widget)
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_export_tab(self):
        """Create the export configuration tab."""
        from PySide6.QtWidgets import QWidget
        
        export_widget = QWidget()
        export_layout = QVBoxLayout(export_widget)
        
        # Dimension selection
        self.dim_widget = DimensionSelectionWidget()
        
        # Output path selection
        self.output_widget = OutputSelectionWidget()
        
        # Export button
        self.export_widget = ExportButtonWidget()
        
        # Add to layout
        export_layout.addWidget(self.dim_widget)
        export_layout.addWidget(self.output_widget)
        export_layout.addWidget(self.export_widget)
        export_layout.addStretch()
        
        return export_widget
    
    def init_handlers(self):
        """Initialize event handlers."""
        self.file_handler = ND2FileHandler(self)
        self.export_handler = TiffExportHandler(self)
        self.event_handler = GUIEventHandler(self)
    
    def connect_signals(self):
        """Connect widget signals to handlers."""
        # File selection
        self.file_widget.file_selected.connect(
            self.event_handler.handle_file_selection
        )
        
        # Export request
        self.export_widget.export_requested.connect(
            self.event_handler.handle_export_request
        )
    
    def set_loading_state(self, loading: bool):
        """Update UI state during file loading."""
        self.file_widget.load_btn.setEnabled(not loading)
        if loading:
            self.progress_widget.start_indeterminate()
            self.set_status("Loading ND2 file...")
        else:
            self.progress_widget.hide_progress()
    
    def set_exporting_state(self, exporting: bool):
        """Update UI state during export."""
        self.export_widget.setEnabled(not exporting)
        if exporting:
            self.progress_widget.start_progress()
            self.set_status("Exporting to TIFF...")
        else:
            self.progress_widget.hide_progress()
    
    def update_file_info(self, info: Dict[str, Any]):
        """Update the display with file information."""
        self.nd2_info = info
        self.info_widget.set_file_info(info)
        self.dim_widget.set_dimensions(info['dimensions'])
    
    def update_progress(self, value: int):
        """Update progress bar during export."""
        self.progress_widget.setValue(value)
    
    def enable_export(self, enabled: bool):
        """Enable or disable export functionality."""
        self.export_widget.set_enabled(enabled)
    
    def set_status(self, message: str):
        """Update status bar message."""
        self.statusBar().showMessage(message)


def main():
    """Main entry point for the GUI application."""
    logger.info("Starting ND2 GUI application")
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    logger.debug("Creating main window")
    window = ND2ViewerApp()
    window.show()
    logger.debug("Main window shown")
    
    logger.info("Starting application event loop")
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
