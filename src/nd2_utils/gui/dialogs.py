"""
Custom dialog widgets for the ND2 viewer GUI.
"""

import logging
import numpy as np
from typing import Dict, Any, Tuple, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialogButtonBox, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt

from ..utils.dimensions import DimensionParser

logger = logging.getLogger(__name__)


class ExportConfirmationDialog(QDialog):
    """Dialog for confirming export with dimensions and file size estimate."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Export")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.confirmed = False
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Export Summary")
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Export details frame
        details_group = QGroupBox("Export Details")
        details_layout = QGridLayout(details_group)
        
        # Labels for details
        self.dimensions_label = QLabel("Dimensions: ")
        self.file_size_label = QLabel("Estimated file size: ")
        self.shape_label = QLabel("Output shape: ")
        
        details_layout.addWidget(QLabel("Dimensions:"), 0, 0)
        details_layout.addWidget(self.dimensions_label, 0, 1)
        
        details_layout.addWidget(QLabel("Output shape:"), 1, 0)
        details_layout.addWidget(self.shape_label, 1, 1)
        
        details_layout.addWidget(QLabel("Estimated size:"), 2, 0)
        details_layout.addWidget(self.file_size_label, 2, 1)
        
        layout.addWidget(details_group)
        
        # Warning message
        warning_label = QLabel("⚠ Please review the export details above before proceeding.")
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(warning_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        continue_button = button_box.addButton("Continue", QDialogButtonBox.AcceptRole)
        continue_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        
        layout.addWidget(button_box)
    
    def set_export_info(self, dimensions: Dict[str, Any], selection: Dict[str, Any]):
        """Set the export information and calculate estimated file size."""
        logger.debug(f"Setting export info with dimensions: {dimensions}")
        logger.debug(f"Selection: {selection}")
        
        # Calculate resulting dimensions
        result_dims = {}
        
        # Map axis letters to selection keys
        axis_map = {
            'T': 'time',
            'P': 'position',
            'C': 'channel',
            'Z': 'z'
        }
        
        for axis in ['T', 'P', 'C', 'Z']:
            if axis in dimensions:
                key = axis_map.get(axis)
                if key in selection and selection[key] is not None:
                    # Parse selection
                    if isinstance(selection[key], tuple) and len(selection[key]) == 2:
                        start, end = selection[key]
                        if start == end:
                            result_dims[axis] = 1
                        else:
                            result_dims[axis] = end - start + 1
                    else:
                        result_dims[axis] = 1
                else:
                    result_dims[axis] = dimensions[axis]['size']
        
        # Add Y and X dimensions
        if 'Y' in dimensions:
            result_dims['Y'] = dimensions['Y']['size']
        if 'X' in dimensions:
            result_dims['X'] = dimensions['X']['size']
        
        # Format dimensions string
        dims_str = []
        shape_info = []
        for axis in ['T', 'P', 'C', 'Z', 'Y', 'X']:
            if axis in result_dims:
                if axis in ['T', 'P', 'C', 'Z']:
                    dims_str.append(f"{axis}={result_dims[axis]}")
                shape_info.append(str(result_dims[axis]))
        
        dimensions_text = ", ".join(dims_str) if dims_str else "Full resolution"
        self.dimensions_label.setText(dimensions_text)
        
        shape_text = f"({' × '.join(shape_info)})"
        self.shape_label.setText(shape_text)
        
        # Calculate estimated file size
        # Use uint16 as typical export format (2 bytes per pixel)
        total_pixels = 1
        for size in result_dims.values():
            total_pixels *= size
        
        # Estimate: uint16 (2 bytes) + some overhead for TIFF metadata (typically 1-5%)
        estimated_bytes = total_pixels * 2
        # Add 10% overhead for metadata and compression
        estimated_bytes = int(estimated_bytes * 1.1)
        
        # Format file size
        if estimated_bytes < 1024:
            size_text = f"{estimated_bytes} bytes"
        elif estimated_bytes < 1024 * 1024:
            size_text = f"{estimated_bytes / 1024:.1f} KB"
        elif estimated_bytes < 1024 * 1024 * 1024:
            size_text = f"{estimated_bytes / (1024 * 1024):.1f} MB"
        else:
            size_text = f"{estimated_bytes / (1024 * 1024 * 1024):.1f} GB"
        
        self.file_size_label.setText(size_text)
        
        # Add warning for large files
        if estimated_bytes > 1024 * 1024 * 1024:  # > 1 GB
            warning_text = "⚠ Large file size detected! This export will create a very large file. Consider reducing your selection."
            self.findChild(QLabel).setText(warning_text)
            self.findChild(QLabel).setStyleSheet("color: red; font-weight: bold;")
    
    @staticmethod
    def confirm_export(parent, dimensions: Dict[str, Any], selection: Dict[str, Any]) -> bool:
        """Show the export confirmation dialog and return True if user confirms."""
        dialog = ExportConfirmationDialog(parent)
        dialog.set_export_info(dimensions, selection)
        
        result = dialog.exec_()
        return result == QDialog.Accepted
