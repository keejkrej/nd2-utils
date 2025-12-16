"""
Reusable GUI components for ND2 viewer.
"""

from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
    QComboBox, QSpinBox, QCheckBox, QProgressBar,
    QTabWidget, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class FileSelectionWidget(QGroupBox):
    """Widget for ND2 file selection."""
    
    file_selected = Signal(str)
    
    def __init__(self):
        super().__init__("ND2 File Selection")
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select ND2 file...")
        self.file_path_edit.setReadOnly(True)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_file)
        
        self.load_btn = QPushButton("Load File")
        self.load_btn.clicked.connect(self.load_file)
        self.load_btn.setEnabled(False)
        
        layout.addWidget(QLabel("File:"))
        layout.addWidget(self.file_path_edit)
        layout.addWidget(self.browse_btn)
        layout.addWidget(self.load_btn)
    
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ND2 File", "", "ND2 Files (*.nd2);;All Files (*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            self.load_btn.setEnabled(True)
    
    def load_file(self):
        file_path = self.file_path_edit.text()
        if file_path:
            self.file_selected.emit(file_path)


class DimensionSelectionWidget(QGroupBox):
    """Widget for dimension selection with range support."""
    
    def __init__(self):
        super().__init__("Dimension Selection")
        self.init_ui()
        self.set_dimensions({})
    
    def init_ui(self):
        layout = QGridLayout(self)
        
        # Position/View/P
        self.position_check = QCheckBox("Position/View/P")
        self.position_input = QLineEdit()
        self.position_input.setPlaceholderText("e.g., 0 or 0-1")
        self.position_input.setEnabled(False)
        
        # Channel/C
        self.channel_check = QCheckBox("Channel/C")
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("e.g., 0 or 0-1")
        self.channel_input.setEnabled(False)
        
        # Time/T
        self.time_check = QCheckBox("Time/T")
        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("e.g., 0 or 0-1")
        self.time_input.setEnabled(False)
        
        # Z-stack/Z
        self.z_check = QCheckBox("Z-stack/Z")
        self.z_input = QLineEdit()
        self.z_input.setPlaceholderText("e.g., 0 or 0-1")
        self.z_input.setEnabled(False)
        
        # Add to layout
        layout.addWidget(self.position_check, 1, 0)
        layout.addWidget(self.position_input, 1, 1, 1, 2)
        
        layout.addWidget(self.channel_check, 2, 0)
        layout.addWidget(self.channel_input, 2, 1, 1, 2)
        
        layout.addWidget(self.time_check, 3, 0)
        layout.addWidget(self.time_input, 3, 1, 1, 2)
        
        layout.addWidget(self.z_check, 4, 0)
        layout.addWidget(self.z_input, 4, 1, 1, 2)
        
        # Connect signals
        self.position_check.toggled.connect(self._on_position_check_toggled)
        self.channel_check.toggled.connect(self._on_channel_check_toggled)
        self.time_check.toggled.connect(self._on_time_check_toggled)
        self.z_check.toggled.connect(self._on_z_check_toggled)
    
    def _on_position_check_toggled(self, checked):
        self.position_input.setEnabled(checked)
    
    def _on_channel_check_toggled(self, checked):
        self.channel_input.setEnabled(checked)
    
    def _on_time_check_toggled(self, checked):
        self.time_input.setEnabled(checked)
    
    def _on_z_check_toggled(self, checked):
        self.z_input.setEnabled(checked)
    
    def _parse_range(self, text):
        """Parse a range string like '0' or '0-1' into (start, end) tuple."""
        text = text.strip()
        if not text:
            return None, None
        
        if '-' in text:
            parts = text.split('-')
            if len(parts) == 2:
                try:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    return start, end
                except ValueError:
                    pass
        else:
            try:
                value = int(text)
                return value, value
            except ValueError:
                pass
        
        return None, None
    
    def set_dimensions(self, dimensions):
        """Update dimension ranges and visibility."""
        # Reset all controls
        self.position_check.setChecked(False)
        self.position_check.setEnabled(False)
        self.position_input.clear()
        
        self.channel_check.setChecked(False)
        self.channel_check.setEnabled(False)
        self.channel_input.clear()
        
        self.time_check.setChecked(False)
        self.time_check.setEnabled(False)
        self.time_input.clear()
        
        self.z_check.setChecked(False)
        self.z_check.setEnabled(False)
        self.z_input.clear()
        
        # Update based on available dimensions
        if 'P' in dimensions:
            size = dimensions['P']['size']
            self.position_check.setEnabled(True)
            self.position_input.setPlaceholderText(f"e.g., 0 or 0-{size-1}")
        
        if 'C' in dimensions:
            size = dimensions['C']['size']
            self.channel_check.setEnabled(True)
            self.channel_input.setPlaceholderText(f"e.g., 0 or 0-{size-1}")
        
        if 'T' in dimensions:
            size = dimensions['T']['size']
            self.time_check.setEnabled(True)
            self.time_input.setPlaceholderText(f"e.g., 0 or 0-{size-1}")
        
        if 'Z' in dimensions:
            size = dimensions['Z']['size']
            self.z_check.setEnabled(True)
            self.z_input.setPlaceholderText(f"e.g., 0 or 0-{size-1}")
    
    def get_selection(self):
        """Get current dimension selection."""
        return {
            'position': self._parse_range(self.position_input.text()) if self.position_check.isChecked() else None,
            'channel': self._parse_range(self.channel_input.text()) if self.channel_check.isChecked() else None,
            'time': self._parse_range(self.time_input.text()) if self.time_check.isChecked() else None,
            'z': self._parse_range(self.z_input.text()) if self.z_check.isChecked() else None,
        }


class OutputSelectionWidget(QGroupBox):
    """Widget for output file selection."""
    
    def __init__(self):
        super().__init__("Output Settings")
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Select output OME-TIFF file...")
        self.output_path_edit.setReadOnly(True)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_output_file)
        
        layout.addWidget(QLabel("Output:"))
        layout.addWidget(self.output_path_edit)
        layout.addWidget(self.browse_btn)
    
    def browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save OME-TIFF File", "", "OME-TIFF Files (*.ome.tif *.ome.tiff);;TIFF Files (*.tif *.tiff)"
        )
        if file_path:
            if not file_path.lower().endswith(('.ome.tif', '.ome.tiff', '.tif', '.tiff')):
                file_path += '.ome.tif'
            self.output_path_edit.setText(file_path)
    
    def get_output_path(self):
        """Get the selected output path."""
        return self.output_path_edit.text()


class FileInfoWidget(QTextEdit):
    """Widget for displaying file information."""
    
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))
        self.clear()
    
    def clear(self):
        """Clear the content."""
        super().clear()
        self.setText("No file loaded")
    
    def set_file_info(self, info):
        """Display file information."""
        lines = []
        lines.append("=== ND2 File Information ===")
        lines.append(f"Path: {info['path']}")
        lines.append(f"Legacy format: {info['is_legacy']}")
        lines.append("")
        
        lines.append("=== Dimensions ===")
        lines.append(f"Shape: {info['shape']}")
        lines.append(f"Size: {info['size']} samples")
        lines.append(f"Data type: {info['dtype']}")
        lines.append(f"Axes: {info['axes']}")
        lines.append("")
        
        # Add dimension details
        from ..utils.dimensions import DimensionParser
        lines.append(DimensionParser.get_dimension_info_text(info['dimensions']))
        
        lines.append("=== Pixel Size ===")
        pixel_size = info['pixel_size']
        for key, value in pixel_size.items():
            lines.append(f"{key}: {value}")
        lines.append("")
        
        lines.append("=== Attributes ===")
        for key, value in list(info['attributes'].items())[:10]:
            lines.append(f"{key}: {value}")
        if len(info['attributes']) > 10:
            lines.append("... (truncated)")
        
        self.setText('\n'.join(lines))


class ExportButtonWidget(QWidget):
    """Widget for export button control."""
    
    export_requested = Signal(dict)  # Export parameters
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setEnabled(False)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.export_btn = QPushButton("Export to OME-TIFF")
        self.export_btn.clicked.connect(self.request_export)
        
        layout.addWidget(self.export_btn)
        layout.addStretch()
    
    def request_export(self):
        """Emit export request signal."""
        self.export_requested.emit({})
    
    def set_enabled(self, enabled):
        """Enable or disable the export button."""
        self.export_btn.setEnabled(enabled)
        super().setEnabled(enabled)


class ProgressWidget(QProgressBar):
    """Widget for showing progress."""
    
    def __init__(self):
        super().__init__()
        self.setVisible(False)
    
    def start_indeterminate(self):
        """Show indeterminate progress."""
        self.setVisible(True)
        self.setRange(0, 0)
    
    def start_progress(self):
        """Show determinate progress."""
        self.setVisible(True)
        self.setRange(0, 100)
        self.setValue(0)
    
    def hide_progress(self):
        """Hide the progress bar."""
        self.setVisible(False)
