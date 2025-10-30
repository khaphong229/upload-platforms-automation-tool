#!/usr/bin/env python3
"""
PyQt5 AI Settings Dialog for configuring AI providers and managing prompts
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QSlider, QSpinBox, QTextEdit, QListWidget,
    QGroupBox, QFormLayout, QMessageBox, QDialog, QDialogButtonBox,
    QTabWidget, QRadioButton, QButtonGroup
)
import logging
from services.ai import AIConfig, PromptManager

logger = logging.getLogger(__name__)


class AISettingsDialog(QDialog):
    """Dialog for AI configuration and prompt management"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Settings")
        self.resize(900, 700)
        self.setModal(True)

        self.ai_config = AIConfig()
        self.prompt_manager = PromptManager()

        self._build_ui()
        self.load_current_settings()

    def _build_ui(self):
        """Build the UI"""
        main_layout = QVBoxLayout(self)

        # Create tab widget
        tabs = QTabWidget()

        # Provider configuration tab
        provider_tab = QWidget()
        self._build_provider_tab(provider_tab)
        tabs.addTab(provider_tab, "AI Provider")

        # Prompt management tab
        prompt_tab = QWidget()
        self._build_prompt_tab(prompt_tab)
        tabs.addTab(prompt_tab, "Prompt Management")

        main_layout.addWidget(tabs)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addLayout(self._create_button_layout())

    def _build_provider_tab(self, parent):
        """Build the provider configuration tab"""
        layout = QVBoxLayout(parent)

        # Provider selection group
        provider_group = QGroupBox("AI Provider Selection")
        provider_layout = QVBoxLayout()

        provider_select_layout = QHBoxLayout()
        provider_select_layout.addWidget(QLabel("Active Provider:"))

        self.provider_combo = QComboBox()
        providers = list(self.ai_config.get_all_providers().keys())
        self.provider_combo.addItems(providers)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_select_layout.addWidget(self.provider_combo)
        provider_select_layout.addStretch()

        provider_layout.addLayout(provider_select_layout)
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # Provider settings group (dynamic based on selection)
        self.provider_settings_group = QGroupBox("Provider Settings")
        self.provider_settings_layout = QVBoxLayout()
        self.provider_settings_group.setLayout(self.provider_settings_layout)
        layout.addWidget(self.provider_settings_group)

        layout.addStretch()

    def _on_provider_changed(self, provider_name):
        """Handle provider selection change"""
        self._load_provider_settings(provider_name)

    def _load_provider_settings(self, provider_name):
        """Load settings for the selected provider"""
        # Clear existing widgets
        while self.provider_settings_layout.count():
            item = self.provider_settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        provider_config = self.ai_config.get_provider_config(provider_name)
        provider_info = self.ai_config.get_all_providers().get(provider_name, {})

        form_layout = QFormLayout()

        # Enabled checkbox
        self.enabled_checkbox = QCheckBox("Enable this provider")
        self.enabled_checkbox.setChecked(provider_config.get('enabled', False))
        form_layout.addRow("", self.enabled_checkbox)

        # API Key
        if provider_info.get('requires_api_key'):
            self.api_key_edit = QLineEdit()
            self.api_key_edit.setText(provider_config.get('api_key', ''))
            self.api_key_edit.setEchoMode(QLineEdit.Password)

            key_layout = QHBoxLayout()
            key_layout.addWidget(self.api_key_edit)

            show_key_btn = QPushButton("Show")
            show_key_btn.setCheckable(True)
            show_key_btn.toggled.connect(
                lambda checked: self.api_key_edit.setEchoMode(
                    QLineEdit.Normal if checked else QLineEdit.Password
                )
            )
            key_layout.addWidget(show_key_btn)

            form_layout.addRow("API Key:", key_layout)

        # Custom API URL (for custom provider)
        if provider_name == 'custom':
            self.api_url_edit = QLineEdit()
            self.api_url_edit.setText(provider_config.get('api_url', ''))
            self.api_url_edit.setPlaceholderText("https://api.example.com/v1/chat/completions")
            form_layout.addRow("API URL:", self.api_url_edit)

        # Model selection
        models = provider_info.get('models', [])
        if models:
            self.model_combo = QComboBox()
            self.model_combo.addItems(models)
            current_model = provider_config.get('model', models[0])
            idx = self.model_combo.findText(current_model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            form_layout.addRow("Model:", self.model_combo)

        # Temperature
        temp_layout = QHBoxLayout()
        self.temperature_slider = QSlider(Qt.Horizontal)
        self.temperature_slider.setMinimum(0)
        self.temperature_slider.setMaximum(100)
        self.temperature_slider.setValue(int(provider_config.get('temperature', 0.7) * 100))

        self.temperature_label = QLabel(f"{provider_config.get('temperature', 0.7):.2f}")
        self.temperature_slider.valueChanged.connect(
            lambda v: self.temperature_label.setText(f"{v/100:.2f}")
        )

        temp_layout.addWidget(self.temperature_slider)
        temp_layout.addWidget(self.temperature_label)
        form_layout.addRow("Temperature:", temp_layout)

        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setMinimum(100)
        self.max_tokens_spin.setMaximum(8000)
        self.max_tokens_spin.setSingleStep(100)
        self.max_tokens_spin.setValue(provider_config.get('max_tokens', 1000))
        form_layout.addRow("Max Tokens:", self.max_tokens_spin)

        self.provider_settings_layout.addLayout(form_layout)

        # Save button
        save_btn = QPushButton("Save Provider Settings")
        save_btn.clicked.connect(self._save_provider_settings)
        self.provider_settings_layout.addWidget(save_btn)

    def _save_provider_settings(self):
        """Save the provider settings"""
        provider_name = self.provider_combo.currentText()

        config = {
            'enabled': self.enabled_checkbox.isChecked()
        }

        if hasattr(self, 'api_key_edit'):
            config['api_key'] = self.api_key_edit.text()

        if hasattr(self, 'api_url_edit'):
            config['api_url'] = self.api_url_edit.text()

        if hasattr(self, 'model_combo'):
            config['model'] = self.model_combo.currentText()

        config['temperature'] = self.temperature_slider.value() / 100.0
        config['max_tokens'] = self.max_tokens_spin.value()

        # Save configuration
        if self.ai_config.update_provider_config(provider_name, **config):
            # Set as active provider if enabled
            if config['enabled']:
                self.ai_config.set_active_provider(provider_name)

            QMessageBox.information(self, "Success",
                f"Provider '{provider_name}' settings saved successfully!")
            logger.info(f"Saved settings for provider: {provider_name}")
        else:
            QMessageBox.critical(self, "Error", "Failed to save provider settings")

    def _build_prompt_tab(self, parent):
        """Build the prompt management tab"""
        layout = QVBoxLayout(parent)

        # Prompt type selection
        type_group = QGroupBox("Prompt Type")
        type_layout = QHBoxLayout()

        self.prompt_type_group = QButtonGroup()
        self.blog_radio = QRadioButton("Blog Post")
        self.tiktok_radio = QRadioButton("TikTok Caption")
        self.blog_radio.setChecked(True)

        self.prompt_type_group.addButton(self.blog_radio)
        self.prompt_type_group.addButton(self.tiktok_radio)

        self.blog_radio.toggled.connect(self._refresh_prompt_list)

        type_layout.addWidget(self.blog_radio)
        type_layout.addWidget(self.tiktok_radio)
        type_layout.addStretch()
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Prompt list and controls
        list_group = QGroupBox("Available Prompts")
        list_layout = QVBoxLayout()

        self.prompt_list = QListWidget()
        self.prompt_list.itemSelectionChanged.connect(self._on_prompt_selected)
        list_layout.addWidget(self.prompt_list)

        # Prompt buttons
        btn_layout = QHBoxLayout()
        new_btn = QPushButton("New Prompt")
        new_btn.clicked.connect(self._new_prompt)
        edit_btn = QPushButton("Edit Prompt")
        edit_btn.clicked.connect(self._edit_prompt)
        delete_btn = QPushButton("Delete Prompt")
        delete_btn.clicked.connect(self._delete_prompt)
        default_btn = QPushButton("Set as Default")
        default_btn.clicked.connect(self._set_default_prompt)

        btn_layout.addWidget(new_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(default_btn)
        btn_layout.addStretch()

        list_layout.addLayout(btn_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # Prompt preview
        preview_group = QGroupBox("Prompt Preview")
        preview_layout = QVBoxLayout()

        self.prompt_preview = QTextEdit()
        self.prompt_preview.setReadOnly(True)
        preview_layout.addWidget(self.prompt_preview)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Initial load
        self._refresh_prompt_list()

    def _get_current_prompt_type(self):
        """Get the currently selected prompt type"""
        return "blog" if self.blog_radio.isChecked() else "tiktok"

    def _refresh_prompt_list(self):
        """Refresh the prompt list"""
        self.prompt_list.clear()

        prompt_type = self._get_current_prompt_type()
        prompts = self.prompt_manager.get_prompt_names(prompt_type)

        # Get currently selected prompt for this type
        selected_prompt_id = self.ai_config.get_selected_prompt(
            'blog_post' if prompt_type == 'blog' else 'tiktok_caption'
        )

        for prompt_id, prompt_name in prompts:
            display_name = f"{'★ ' if prompt_id == selected_prompt_id else ''}{prompt_name}"
            item = self.prompt_list.addItem(display_name)
            # Store prompt_id in item data
            self.prompt_list.item(self.prompt_list.count() - 1).setData(Qt.UserRole, prompt_id)

    def _on_prompt_selected(self):
        """Handle prompt selection"""
        items = self.prompt_list.selectedItems()
        if not items:
            return

        prompt_id = items[0].data(Qt.UserRole)
        prompt = self.prompt_manager.get_prompt(prompt_id)

        if prompt:
            self.prompt_preview.setPlainText(prompt['template'])

    def _new_prompt(self):
        """Create a new prompt"""
        dialog = PromptEditDialog(self, self.prompt_manager,
                                 prompt_type=self._get_current_prompt_type())
        if dialog.exec_() == QDialog.Accepted:
            self._refresh_prompt_list()

    def _edit_prompt(self):
        """Edit selected prompt"""
        items = self.prompt_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "Warning", "Please select a prompt to edit")
            return

        prompt_id = items[0].data(Qt.UserRole)
        prompt = self.prompt_manager.get_prompt(prompt_id)

        if prompt and prompt.get('is_default'):
            QMessageBox.warning(self, "Warning",
                "Cannot edit default prompts. Create a new prompt instead.")
            return

        dialog = PromptEditDialog(self, self.prompt_manager, prompt_id=prompt_id)
        if dialog.exec_() == QDialog.Accepted:
            self._refresh_prompt_list()

    def _delete_prompt(self):
        """Delete selected prompt"""
        items = self.prompt_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "Warning", "Please select a prompt to delete")
            return

        prompt_id = items[0].data(Qt.UserRole)
        prompt = self.prompt_manager.get_prompt(prompt_id)

        if prompt and prompt.get('is_default'):
            QMessageBox.warning(self, "Warning", "Cannot delete default prompts.")
            return

        reply = QMessageBox.question(self, "Confirm Delete",
            f"Delete prompt '{prompt['name']}'?",
            QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.prompt_manager.delete_prompt(prompt_id):
                self._refresh_prompt_list()
                self.prompt_preview.clear()
                QMessageBox.information(self, "Success", "Prompt deleted successfully")

    def _set_default_prompt(self):
        """Set selected prompt as default"""
        items = self.prompt_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "Warning",
                "Please select a prompt to set as default")
            return

        prompt_id = items[0].data(Qt.UserRole)
        prompt_type = self._get_current_prompt_type()

        config_key = 'blog_post' if prompt_type == 'blog' else 'tiktok_caption'
        if self.ai_config.set_selected_prompt(config_key, prompt_id):
            self._refresh_prompt_list()
            QMessageBox.information(self, "Success",
                f"Set as default prompt for {prompt_type}")

    def _create_button_layout(self):
        """Create dialog button layout"""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        return btn_layout

    def load_current_settings(self):
        """Load current settings"""
        active_provider = self.ai_config.get_active_provider()
        idx = self.provider_combo.findText(active_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)


class PromptEditDialog(QDialog):
    """Dialog for creating/editing prompts"""

    def __init__(self, parent, prompt_manager, prompt_id=None, prompt_type="blog"):
        super().__init__(parent)
        self.prompt_manager = prompt_manager
        self.prompt_id = prompt_id
        self.prompt_type = prompt_type

        self.setWindowTitle("Edit Prompt" if prompt_id else "New Prompt")
        self.resize(700, 500)
        self.setModal(True)

        # Load existing prompt if editing
        if prompt_id:
            self.prompt_data = prompt_manager.get_prompt(prompt_id)
        else:
            self.prompt_data = None

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI"""
        layout = QVBoxLayout(self)

        # Prompt name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Prompt Name:"))
        self.name_edit = QLineEdit()
        if self.prompt_data:
            self.name_edit.setText(self.prompt_data['name'])
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Help text
        help_text = "Use placeholders: {title}, {video_title}, {video_description}, {apk_links_text}"
        if self.prompt_type == "tiktok":
            help_text = "Use placeholders: {title}, {blog_url}, {max_length}"

        help_label = QLabel(help_text)
        help_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(help_label)

        # Prompt template
        layout.addWidget(QLabel("Prompt Template:"))
        self.template_edit = QTextEdit()
        if self.prompt_data:
            self.template_edit.setPlainText(self.prompt_data['template'])
        layout.addWidget(self.template_edit)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._save_prompt)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _save_prompt(self):
        """Save the prompt"""
        name = self.name_edit.text().strip()
        template = self.template_edit.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a prompt name")
            return

        if not template:
            QMessageBox.warning(self, "Warning", "Please enter a prompt template")
            return

        # Generate prompt_id from name if new
        if not self.prompt_id:
            prompt_id = name.lower().replace(' ', '_')
            # Ensure unique ID
            counter = 1
            original_id = prompt_id
            while self.prompt_manager.get_prompt(prompt_id):
                prompt_id = f"{original_id}_{counter}"
                counter += 1

            # Add new prompt
            if self.prompt_manager.add_prompt(prompt_id, name, template, self.prompt_type):
                QMessageBox.information(self, "Success", "Prompt created successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to create prompt")
        else:
            # Update existing prompt
            if self.prompt_manager.update_prompt(self.prompt_id, name=name, template=template):
                QMessageBox.information(self, "Success", "Prompt updated successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update prompt")
