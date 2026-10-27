"""
theme.py
---------
The app's stylesheet, now generated for two colour palettes - Light and
Dark - from one shared structural template, so a theme switch changes
ONLY colours: every border-radius, padding, margin, and selector stays
identical between the two. This is what "Add a theme setting, don't
redesign anything" means in code - LIGHT_THEME_QSS is exactly the
existing look from before this feature (nothing about it changed), and
DARK_THEME_QSS is the same rules with a dark palette substituted in.

Screens that set a specific accent colour inline (success green, warning
orange, error red, info blue - e.g. "Cash matches" / "difference
detected" messages) keep using the same hex values in both themes. That
is a deliberate, scoped choice: those are semantic status colours, not
part of the light/dark background system, and touching every such inline
colour across the app would be exactly the kind of broad redesign this
patch is explicitly asked not to do.
"""

_TEMPLATE = """
QWidget {{
    background-color: {app_bg};
    color: {text_primary};
    font-family: "Segoe UI", sans-serif;
    font-size: 10.5pt;
}}

QMainWindow, QDialog {{
    background-color: {app_bg};
}}

QFrame {{
    background-color: {card_bg};
    border-radius: 10px;
    border: none;
}}

QLabel {{
    background: transparent;
    border: none;
}}

QPushButton {{
    background-color: {button_bg};
    color: {text_primary};
    border: 1px solid {button_border};
    border-radius: 8px;
    padding: 8px 14px;
}}
QPushButton:hover {{
    background-color: {button_hover_bg};
    border: 1px solid {accent};
}}
QPushButton:pressed {{
    background-color: {button_pressed_bg};
}}
QPushButton:disabled {{
    color: {text_disabled};
    background-color: {button_disabled_bg};
    border: 1px solid {button_disabled_border};
}}

QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QDateEdit, QTextEdit {{
    background-color: {input_bg};
    color: {text_primary};
    border: 1px solid {input_border};
    border-radius: 8px;
    padding: 5px 8px;
    selection-background-color: {accent};
    selection-color: {selection_text};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {{
    border: 1px solid {accent};
}}
QComboBox::drop-down {{
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {input_bg};
    color: {text_primary};
    selection-background-color: {accent};
    selection-color: {selection_text};
    border: 1px solid {input_border};
}}

QTableWidget, QListWidget {{
    background-color: {card_bg};
    alternate-background-color: {app_bg};
    color: {text_primary};
    border: 1px solid {card_border};
    border-radius: 10px;
    gridline-color: {table_grid};
}}
QHeaderView::section {{
    background-color: {table_header_bg};
    color: {table_header_text};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {card_border};
    font-weight: bold;
}}
QTableWidget::item:selected, QListWidget::item:selected {{
    background-color: {accent};
    color: {selection_text};
}}

QScrollBar:vertical {{
    background: {app_bg};
    width: 12px;
}}
QScrollBar::handle:vertical {{
    background: {scrollbar_handle};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {scrollbar_handle_hover};
}}

QProgressBar {{
    border: none;
    background-color: {table_header_bg};
    border-radius: 6px;
}}
QProgressBar::chunk {{
    background-color: {accent};
    border-radius: 6px;
}}

QToolTip {{
    background-color: {tooltip_bg};
    color: {tooltip_text};
    border: 1px solid {accent};
}}

/* Sidebar navigation (ui/main_window.py) */
QPushButton#sidebarButton {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 14px;
    color: {sidebar_text};
    font-size: 10.5pt;
}}
QPushButton#sidebarButton:hover {{
    background-color: {sidebar_hover};
    border: none;
}}
QPushButton#sidebarButton:checked {{
    background-color: {sidebar_active_bg};
    color: {sidebar_active_text};
    font-weight: bold;
}}

QFrame#sidebarFrame {{
    border-radius: 0px;
    border: none;
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 {sidebar_gradient_start}, stop: 1 {sidebar_gradient_end}
    );
}}

QFrame#headerFrame {{
    background-color: {header_bg};
    border-radius: 0px;
    border: none;
    border-bottom: 1px solid {card_border};
}}
"""

# Unchanged from before this feature - this IS the existing appearance.
LIGHT_COLORS = {
    "app_bg": "#f4f8f6",
    "card_bg": "#ffffff",
    "card_border": "#e0ece7",
    "text_primary": "#26332e",
    "text_secondary": "#6b7d76",
    "text_disabled": "#a9b6b0",
    "input_bg": "#ffffff",
    "input_border": "#cfe3da",
    "accent": "#2f9e7a",
    "table_header_bg": "#eaf6f0",
    "table_header_text": "#3d5049",
    "table_grid": "#eef4f1",
    "scrollbar_handle": "#bcd6cb",
    "scrollbar_handle_hover": "#9ec3b6",
    "tooltip_bg": "#26332e",
    "tooltip_text": "#eaf6f0",
    "sidebar_gradient_start": "#1f6f57",
    "sidebar_gradient_end": "#2f9e7a",
    "sidebar_text": "#eaf6f0",
    "sidebar_hover": "rgba(255, 255, 255, 40)",
    "sidebar_active_bg": "#ffffff",
    "sidebar_active_text": "#1f6f57",
    "header_bg": "#ffffff",
    "button_bg": "#ffffff",
    "button_border": "#cfe3da",
    "button_hover_bg": "#eaf6f0",
    "button_pressed_bg": "#dcefe6",
    "button_disabled_bg": "#f0f3f2",
    "button_disabled_border": "#e4eae7",
    "selection_text": "white",
}

# Proper dark background, readable text, same accent colour for brand
# consistency, same structure as Light in every other respect.
DARK_COLORS = {
    "app_bg": "#181c1a",
    "card_bg": "#20261f",
    "card_border": "#333c37",
    "text_primary": "#e7efe9",
    "text_secondary": "#9fb0a8",
    "text_disabled": "#5b675f",
    "input_bg": "#242b25",
    "input_border": "#3a453e",
    "accent": "#3fbd90",
    "table_header_bg": "#232c26",
    "table_header_text": "#bfe3d4",
    "table_grid": "#2e372f",
    "scrollbar_handle": "#3a453e",
    "scrollbar_handle_hover": "#4a5850",
    "tooltip_bg": "#0f1310",
    "tooltip_text": "#e7efe9",
    "sidebar_gradient_start": "#0f2e24",
    "sidebar_gradient_end": "#1c5b45",
    "sidebar_text": "#dcf3ea",
    "sidebar_hover": "rgba(255, 255, 255, 25)",
    "sidebar_active_bg": "#20261f",
    "sidebar_active_text": "#3fbd90",
    "header_bg": "#20261f",
    "button_bg": "#242b25",
    "button_border": "#3a453e",
    "button_hover_bg": "#2b332c",
    "button_pressed_bg": "#181c1a",
    "button_disabled_bg": "#1c211d",
    "button_disabled_border": "#2e372f",
    "selection_text": "#0f1310",
}

LIGHT_THEME_QSS = _TEMPLATE.format(**LIGHT_COLORS)
DARK_THEME_QSS = _TEMPLATE.format(**DARK_COLORS)

# Backward-compatible alias - the app's previous single-theme name,
# still pointing at the (unchanged) light appearance.
APP_THEME_QSS = LIGHT_THEME_QSS


def qss_for(resolved_theme: str) -> str:
    """resolved_theme must already be 'light' or 'dark' (see
    app_settings.resolve_theme for turning a saved 'system' setting into
    one of these)."""
    return DARK_THEME_QSS if resolved_theme == "dark" else LIGHT_THEME_QSS


def colors_for(resolved_theme: str) -> dict:
    """The raw colour dict for a resolved theme - used by screens (login,
    header) that have a few colours set outside the global stylesheet."""
    return DARK_COLORS if resolved_theme == "dark" else LIGHT_COLORS
