"""
Event handlers for the ND2 viewer GUI.
"""

import logging
import os
from typing import Any, Dict

from PySide6.QtWidgets import QMessageBox

from ..processors.nd2_processor import ND2Processor
from ..processors.tiff_exporter import TiffExporter

logger = logging.getLogger(__name__)


class ND2FileHandler:
    """Handles ND2 file loading operations."""

    def __init__(self, gui_app):
        self.gui_app = gui_app
        self.loader = None

    def load_file(self, file_path: str):
        """Load ND2 file in background thread."""
        logger.debug(f"Loading ND2 file: {file_path}")

        if not os.path.exists(file_path):
            logger.warning("File does not exist")
            QMessageBox.warning(None, "Error", "Please select a valid ND2 file.")
            return

        # Update UI state
        self.gui_app.set_loading_state(True)

        # Start loading in background
        self.loader = ND2Processor(file_path)
        self.loader.finished.connect(self.on_file_loaded)
        self.loader.error.connect(self.on_load_error)
        self.loader.start()
        logger.debug("ND2 loader thread started")

    def on_file_loaded(self, info: Dict[str, Any]):
        """Handle successful file load."""
        logger.debug("File loaded successfully")
        self.loader = None

        # Update GUI with file info
        self.gui_app.update_file_info(info)
        self.gui_app.set_loading_state(False)
        self.gui_app.enable_export(True)

        filename = os.path.basename(info["path"])
        self.gui_app.set_status(f"Loaded: {filename}")

    def on_load_error(self, error_msg: str):
        """Handle file load error."""
        logger.error(f"File load error: {error_msg}")
        self.loader = None

        self.gui_app.set_loading_state(False)
        QMessageBox.critical(None, "Error", error_msg)
        self.gui_app.set_status("Error loading file")


class TiffExportHandler:
    """Handles TIFF export operations."""

    def __init__(self, gui_app):
        self.gui_app = gui_app
        self.exporter = None

    def export_file(
        self,
        nd2_path: str,
        output_path: str,
        position: tuple = None,
        channel: tuple = None,
        time: tuple = None,
        z: tuple = None,
    ):
        """Export ND2 file to TIFF in background thread."""
        logger.debug(f"Exporting to TIFF: {output_path}")

        if not output_path:
            logger.warning("No output path selected")
            QMessageBox.warning(None, "Error", "Please select an output file path.")
            return

        # Update UI state
        self.gui_app.set_exporting_state(True)

        # Start exporting in background
        self.exporter = TiffExporter(nd2_path, output_path, position, channel, time, z)
        self.exporter.progress.connect(self.gui_app.update_progress)
        self.exporter.finished.connect(self.on_export_finished)
        self.exporter.error.connect(self.on_export_error)
        self.exporter.start()
        logger.debug("TIFF exporter thread started")

    def on_export_finished(self, output_path: str):
        """Handle successful export."""
        logger.info(f"Export completed: {output_path}")

        # Mark thread for cleanup but don't block
        if self.exporter:
            self.exporter.deleteLater()
            self.exporter = None

        self.gui_app.set_exporting_state(False)
        QMessageBox.information(
            None, "Success", f"Successfully exported to:\n{output_path}"
        )
        self.gui_app.set_status("Export completed")

    def on_export_error(self, error_msg: str):
        """Handle export error."""
        logger.error(f"Export error: {error_msg}")

        # Mark thread for cleanup but don't block
        if self.exporter:
            self.exporter.deleteLater()
            self.exporter = None

        self.gui_app.set_exporting_state(False)
        QMessageBox.critical(None, "Export Error", error_msg)
        self.gui_app.set_status("Export failed")


class GUIEventHandler:
    """Handles general GUI events."""

    def __init__(self, main_window):
        self.main_window = main_window

    def handle_file_selection(self, file_path: str):
        """Handle ND2 file selection."""
        self.main_window.file_handler.load_file(file_path)

    def handle_export_request(self, export_params: dict):
        """Handle export request from GUI with confirmation dialog."""
        nd2_path = self.main_window.nd2_info.get("path", "")
        output_path = self.main_window.output_widget.get_output_path()

        # Check if file is loaded
        if not nd2_path:
            QMessageBox.warning(None, "No File", "Please load an ND2 file first.")
            return

        # Get dimension selection
        dim_selection = self.main_window.dim_widget.get_selection()

        # Import the dialog here to avoid circular imports
        from .dialogs import ExportConfirmationDialog

        # Show confirmation dialog
        if ExportConfirmationDialog.confirm_export(
            self.main_window, self.main_window.nd2_info["dimensions"], dim_selection
        ):
            # User confirmed, proceed with export
            self.main_window.export_handler.export_file(
                nd2_path, output_path, **dim_selection
            )
        else:
            # User cancelled
            logger.debug("Export cancelled by user")
            self.main_window.set_status("Export cancelled")
