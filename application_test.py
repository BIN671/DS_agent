import sys
import os
import json

import support
from main import DeepSeek_API
from support import prompt
import traceback

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QLabel, QStackedWidget, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QMenu, QFrame,
    QSizePolicy, QGraphicsDropShadowEffect, QScrollArea, QDialog, QFormLayout, QCheckBox, QSpinBox, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QColor, QFont


# =============================================================
#  Настройки (settings.json)
# =============================================================
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "api_timeout": 30,
    "max_steps": 30,
    "output_font_size": 12,
}


def load_settings() -> dict:
    data = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return data


def save_settings(data: dict) -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


try:
    import secret_local as secret
except ImportError:
    import secret_example as secret


# =============================================================
#  Палитра — единая, спокойная тёмная тема
# =============================================================
class C:
    bg          = "#0b0d12"
    surface     = "#12151d"
    surface_2   = "#171b25"
    surface_3   = "#1d2230"
    border      = "#242a38"
    border_soft = "#1c212c"
    accent      = "#5b8def"
    accent_hi   = "#7aa4ff"
    accent_lo   = "#4470d0"
    text        = "#e8ebf2"
    text_soft   = "#b6bccb"
    text_dim    = "#6f7789"
    danger      = "#f26a7a"
    success     = "#4ecb9a"
    user_bg     = "#243252"
    user_border = "#31406a"
    bot_bg      = "#161b26"
    bot_border  = "#232a3a"


GLOBAL_STYLE = f"""
QWidget {{
    background-color: {C.bg};
    color: {C.text};
    font-family: 'Segoe UI', 'Inter', 'SF Pro Text', sans-serif;
    font-size: 14px;
}}

QWidget#Root, QMainWindow {{ background-color: {C.bg}; }}

/* ---------- Сайдбар ---------- */
QWidget#Sidebar {{
    background-color: {C.surface};
    border-right: 1px solid {C.border_soft};
}}
QLabel#Brand {{
    color: {C.text};
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.5px;
    background: transparent;
}}
QLabel#BrandAccent {{
    color: {C.accent};
    font-size: 17px;
    font-weight: 700;
    background: transparent;
}}

/* ---------- Карточки ---------- */
QWidget#Card {{
    background-color: {C.surface_2};
    border: 1px solid {C.border_soft};
    border-radius: 14px;
}}
QWidget#CardSoft {{
    background-color: {C.surface};
    border: 1px solid {C.border_soft};
    border-radius: 14px;
}}

/* ---------- Заголовки ---------- */
QLabel#Title {{
    color: {C.text};
    font-size: 22px;
    font-weight: 700;
    background: transparent;
}}
QLabel#Subtitle {{
    color: {C.text_dim};
    font-size: 13px;
    background: transparent;
}}
QLabel#Section {{
    color: {C.text_dim};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    background: transparent;
}}
QLabel#SessionTitle {{
    color: {C.text};
    font-size: 16px;
    font-weight: 600;
    background: transparent;
}}
QLabel#State {{
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 10px;
    background: transparent;
}}

/* ---------- Кнопки ---------- */
QPushButton {{
    background-color: {C.surface_3};
    color: {C.text};
    border: 1px solid {C.border};
    border-radius: 10px;
    padding: 8px 16px;
}}
QPushButton:hover {{
    background-color: {C.border};
    border-color: {C.accent};
}}
QPushButton:pressed {{ background-color: {C.border_soft}; }}
QPushButton:disabled {{
    color: {C.text_dim};
    background-color: {C.surface};
    border-color: {C.border_soft};
}}

QPushButton#Primary {{
    background-color: {C.accent};
    color: #ffffff;
    border: none;
    font-size: 15px;
    font-weight: 600;
    padding: 12px 28px;
    border-radius: 10px;
}}
QPushButton#Primary:hover {{ background-color: {C.accent_hi}; }}
QPushButton#Primary:pressed {{ background-color: {C.accent_lo}; }}
QPushButton#Primary:disabled {{
    background-color: {C.surface_3};
    color: {C.text_dim};
}}

QPushButton#IconBtn {{
    background-color: {C.surface_3};
    color: {C.text_soft};
    border: 1px solid {C.border};
    border-radius: 10px;
    font-size: 16px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#IconBtn:hover {{
    background-color: {C.accent};
    border-color: {C.accent};
    color: #ffffff;
}}

QPushButton#Send {{
    background-color: {C.accent};
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-size: 18px;
    font-weight: 700;
}}
QPushButton#Send:hover {{ background-color: {C.accent_hi}; }}
QPushButton#Send:pressed {{ background-color: {C.accent_lo}; }}
QPushButton#Send:disabled {{
    background-color: {C.surface_3};
    color: {C.text_dim};
}}

/* ---------- Поля ввода ---------- */
QLineEdit {{
    background-color: {C.surface_3};
    color: {C.text};
    border: 1px solid {C.border};
    border-radius: 10px;
    padding: 10px 14px;
    selection-background-color: {C.accent};
    selection-color: #ffffff;
}}
QLineEdit:focus {{ border: 1px solid {C.accent}; }}
QLineEdit:disabled {{
    background-color: {C.surface};
    color: {C.text_dim};
}}

QTextEdit {{
    background-color: {C.surface};
    color: {C.text_soft};
    border: 1px solid {C.border_soft};
    border-radius: 10px;
    padding: 10px;
    selection-background-color: {C.accent};
    selection-color: #ffffff;
    font-family: 'Consolas', 'Cascadia Mono', monospace;
    font-size: 12px;
}}

/* ---------- Список сессий ---------- */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
    color: {C.text_soft};
}}
QListWidget::item {{
    background-color: transparent;
    color: {C.text_soft};
    border-radius: 9px;
    padding: 9px 12px;
    margin: 1px 0;
}}
QListWidget::item:hover {{
    background-color: {C.surface_3};
    color: {C.text};
}}
QListWidget::item:selected {{
    background-color: {C.accent};
    color: #ffffff;
}}

/* ---------- Скроллбары ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C.border};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C.accent}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {C.border};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {C.accent}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ---------- Меню ---------- */
QMenu {{
    background-color: {C.surface_3};
    color: {C.text};
    border: 1px solid {C.border};
    border-radius: 10px;
    padding: 5px;
}}
QMenu::item {{
    padding: 8px 22px;
    border-radius: 6px;
    color: {C.text};
}}
QMenu::item:selected {{
    background-color: {C.accent};
    color: #ffffff;
}}

QSplitter::handle {{
    background-color: transparent;
    width: 8px;
}}
QSplitter::handle:hover {{ background-color: {C.border_soft}; }}
"""


# =============================================================
#  Диалог настроек
# =============================================================
class SettingsDialog(QDialog):
    def __init__(self, mode='global', parent=None, values=None):
        super().__init__(parent)
        self.mode = mode
        values = values or {}
        title = 'Настройки' if mode == 'global' else 'Настройки сессии'
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)

        header = QLabel(title)
        header.setObjectName('Title')
        header.setStyleSheet('font-size:18px;')
        root.addWidget(header)

        form = QFormLayout()
        form.setContentsMargins(0, 8, 0, 8)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        if mode == 'global':
            self.user_token = QLineEdit(values.get('user_token', getattr(secret, 'USER_TOKEN', '')))
            self.user_token.setPlaceholderText('USER_TOKEN…')
            self.session_id = QLineEdit(values.get('session_id', getattr(secret, 'DS_SESSION_ID', '')))
            self.session_id.setPlaceholderText('DS_SESSION_ID…')
            form.addRow(self._lbl('USER_TOKEN'), self.user_token)
            form.addRow(self._lbl('DS_SESSION_ID'), self.session_id)
        else:
            self.font_size = QSpinBox()
            self.font_size.setRange(11, 20)
            self.font_size.setValue(int(values.get('font_size', 14)))
            self.compact = QCheckBox('Компактные пузыри')
            self.compact.setChecked(bool(values.get('compact', False)))
            self.show_log = QCheckBox('Показывать панель лога')
            self.show_log.setChecked(bool(values.get('show_log', True)))
            form.addRow(self._lbl('Размер шрифта'), self.font_size)
            form.addRow(self._lbl('Вид'), self.compact)
            form.addRow(self._lbl('Панели'), self.show_log)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _lbl(text):
        l = QLabel(text)
        l.setStyleSheet('color: #b6bccb; font-size: 13px; background: transparent;')
        return l

    def values(self):
        if self.mode == 'global':
            return {'user_token': self.user_token.text().strip(),
                    'session_id': self.session_id.text().strip()}
        return {'font_size': self.font_size.value(),
                'compact': self.compact.isChecked(),
                'show_log': self.show_log.isChecked()}


# =============================================================
#  MessageWorker
# =============================================================
class MessageWorker(QThread):
    answer = Signal(str)
    error = Signal(str)
    answer_text = Signal(str)

    def __init__(self, api, text: str, parent=None):
        super().__init__(parent)
        self._api = api
        self._text = text

    def run(self):
        try:
            while True:
                ans = self._api.send_message(self._text)
                self.answer.emit(ans)
                self.answer_text.emit(support.extract(ans).get("text", ""))
                response = self._api.execute()
                if response[0] != "continue":
                    break
                self._text = f"{response[0]}: {response[1]}"
                self.answer.emit(self._text)
        except Exception as e:
            self.error.emit(str(e))


# =============================================================
#  Пузырь сообщения
# =============================================================
class Bubble(QWidget):
    """Аккуратный пузырь сообщения с фиксированными цветами."""

    def __init__(self, text: str, role: str = "bot", parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        is_user = role == "user"
        bg = C.user_bg if is_user else C.bot_bg
        border = C.user_border if is_user else C.bot_border

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(0)

        if is_user:
            outer.addStretch(1)

        bubble = QWidget()
        bubble.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        bubble.setMaximumWidth(720)
        bl = QVBoxLayout(bubble)
        bl.setContentsMargins(14, 10, 14, 10)
        bl.setSpacing(4)

        # Автор
        author = QLabel("Вы" if is_user else "DeepSeek")
        author.setStyleSheet(f"""
            color: {C.text_dim};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.6px;
            background: transparent;
        """)
        bl.addWidget(author)

        # Текст
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet(f"""
            color: {C.text};
            font-size: 14px;
            background: transparent;
        """)
        bl.addWidget(body)

        outer.addWidget(bubble)
        if not is_user:
            outer.addStretch(1)


class SystemNote(QLabel):
    def __init__(self, text: str, color: str = C.text_dim, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            color: {color};
            font-size: 12px;
            padding: 4px;
            background: transparent;
        """)


# =============================================================
#  WorkspacePage
# =============================================================
class WorkspacePage(QWidget):
    def __init__(self, title: str = "Новая", parent=None):
        super().__init__(parent)
        self.title = title
        self.api = None
        self._worker = None

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_start_screen())
        self.stack.addWidget(self._build_main_screen())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    # ---------- Start ----------
    def _build_start_screen(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(40, 40, 40, 40)

        layout.addStretch(2)

        card = QWidget()
        card.setObjectName("Card")
        card.setFixedWidth(460)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(36, 40, 36, 36)
        cl.setSpacing(10)

        icon = QLabel("◆")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"color: {C.accent}; font-size: 48px; background: transparent;")

        title = QLabel("DeepSeek Workspace")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Новая сессия. Нажмите «Start», чтобы начать.")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("Primary")
        self.start_button.setMinimumHeight(46)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.on_start)

        self.start_status = QLabel("")
        self.start_status.setAlignment(Qt.AlignCenter)
        self.start_status.setWordWrap(True)
        self.start_status.setStyleSheet(f"color: {C.text_dim}; background: transparent;")
        self.start_status.hide()

        cl.addWidget(icon)
        cl.addSpacing(4)
        cl.addWidget(title)
        cl.addWidget(subtitle)
        cl.addSpacing(14)
        cl.addWidget(self.start_button)
        cl.addWidget(self.start_status)

        layout.addWidget(card, alignment=Qt.AlignCenter)
        layout.addStretch(3)
        return screen

    # ---------- Main ----------
    def _build_main_screen(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        # --- Header ---
        header = QHBoxLayout()
        header.setSpacing(10)

        self.session_label = QLabel(self.title)
        self.session_label.setObjectName("SessionTitle")
        header.addWidget(self.session_label)
        header.addStretch()

        self.session_settings_button = QPushButton("⚙ Настройки")
        self.session_settings_button.setObjectName("IconBtn")
        self.session_settings_button.setToolTip("Настройки этой сессии")
        self.session_settings_button.setCursor(Qt.PointingHandCursor)
        self.session_settings_button.clicked.connect(self.open_session_settings)
        header.addWidget(self.session_settings_button)

        self.state_label = QLabel("●  Готово")
        self.state_label.setObjectName("State")
        self._set_state("Готово", C.success)
        header.addWidget(self.state_label)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- Левая карточка: чат ---
        left = QWidget()
        left.setObjectName("Card")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 16, 16, 16)
        ll.setSpacing(10)

        chat_header = QHBoxLayout()
        lbl_chat = QLabel("ДИАЛОГ")
        lbl_chat.setObjectName("Section")
        chat_header.addWidget(lbl_chat)
        chat_header.addStretch()
        ll.addLayout(chat_header)

        # Скролл-область с пузырями
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(2, 2, 8, 2)
        self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch(1)

        self.chat_scroll.setWidget(self.chat_content)
        ll.addWidget(self.chat_scroll, stretch=1)

        # Поле ввода
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Введите сообщение и нажмите Enter…")
        self.entry.setMinimumHeight(44)
        self.entry.returnPressed.connect(self.on_enter)
        input_row.addWidget(self.entry, stretch=1)

        self.send_button = QPushButton("→")
        self.send_button.setObjectName("Send")
        self.send_button.setFixedSize(50, 44)
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self.on_enter)
        input_row.addWidget(self.send_button)

        ll.addLayout(input_row)

        # --- Правая карточка: лог ---
        right = QWidget()
        right.setObjectName("CardSoft")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.setSpacing(10)

        lbl_log = QLabel("ЛОГ / ОТЛАДКА")
        lbl_log.setObjectName("Section")
        rl.addWidget(lbl_log)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Сырые ответы API…")
        rl.addWidget(self.output, stretch=1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([660, 360])
        layout.addWidget(splitter, stretch=1)
        return screen

    # ---------- Состояние ----------
    def _set_state(self, text: str, color: str):
        self.state_label.setText(f"●  {text}")
        self.state_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background: {C.surface_3};
                border: 1px solid {C.border};
                border-radius: 10px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
        """)

    # ---------- Настройки сессии ----------
    def open_session_settings(self):
        cur = load_settings()
        dlg = SettingsDialog(
            mode='session',
            parent=self,
            values={
                'font_size': cur.get('output_font_size', 14),
                'compact': False,
                'show_log': True,
            },
        )
        if dlg.exec() == QDialog.Accepted:
            v = dlg.values()
            cur['output_font_size'] = v.get('font_size', cur.get('output_font_size', 14))
            save_settings(cur)
            self.apply_settings()

    def apply_settings(self):
        s = load_settings()
        size = int(s.get('output_font_size', 14))
        if hasattr(self, 'output') and self.output is not None:
            self.output.setStyleSheet(f"font-size: {size}px;")

    # ---------- Добавление пузыря ----------
    def _add_bubble(self, text: str, role: str):
        if not text:
            return
        # убрать stretch на конце, вставить пузырь, вернуть stretch
        item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        del item
        self.chat_layout.addWidget(Bubble(text, role))
        self.chat_layout.addStretch(1)
        # прокрутить вниз
        QApplication.processEvents()
        sb = self.chat_scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _add_note(self, text: str, color: str = C.text_dim):
        item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        del item
        self.chat_layout.addWidget(SystemNote(text, color))
        self.chat_layout.addStretch(1)
        QApplication.processEvents()
        sb = self.chat_scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---------- Start ----------
    def on_start(self):
        self.start_button.setEnabled(False)
        self.start_button.setText("Подключение…")
        self.start_status.setText("Запрос к API…")
        self.start_status.setStyleSheet(f"color: {C.text_dim}; background: transparent;")
        self.start_status.show()
        QApplication.processEvents()

        try:
            self.api = DeepSeek_API(secret.USER_TOKEN, secret.DS_SESSION_ID)
            self.api.creat_session()
            ans = self.api.send_message(prompt)
        except Exception:
            self.start_button.setEnabled(True)
            self.start_button.setText("Start")
            self.start_status.setText(f"Ошибка: {traceback.format_exc()}")
            self.start_status.setStyleSheet(f"color: {C.danger}; background: transparent;")
            return

        self.start_status.hide()
        self.start_button.setText("Start")
        self.start_button.setEnabled(True)
        self.stack.setCurrentIndex(1)
        self.output.append(ans)
        self.session_label.setText(self.title)
        self.entry.setFocus()

    # ---------- Enter ----------
    def on_enter(self):
        text = self.entry.text()
        if not text.strip():
            return
        if self._worker is not None and self._worker.isRunning():
            return

        self.entry.setEnabled(False)
        self.send_button.setEnabled(False)
        self.entry.setPlaceholderText("Ожидание ответа…")
        self._set_state("Думает…", C.accent)

        self.output.append(f"> Пользователь:\n{text}\n")
        self._add_bubble(text, "user")

        self._worker = MessageWorker(self.api, text, parent=self)
        self._worker.answer.connect(self._on_message_answer)
        self._worker.answer_text.connect(self._on_message_answer_text)
        self._worker.error.connect(self._on_message_error)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def _on_message_answer(self, ans: str):
        self.output.append(f"> DeepSeek:\n{ans}\n")

    def _on_message_error(self, msg: str):
        self.output.append(f"> [Ошибка]:\n{msg}\n")
        self._add_note(f"Ошибка: {msg}", C.danger)

    def _on_message_answer_text(self, ans_text: str):
        if not ans_text:
            return
        self._add_bubble(ans_text, "bot")

    def _cleanup_worker(self):
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self._set_state("Готово", C.success)
        self.entry.setEnabled(True)
        self.send_button.setEnabled(True)
        self.entry.setPlaceholderText("Введите сообщение и нажмите Enter…")
        self.entry.clear()
        self.entry.setFocus()


# =============================================================
#  MainWindow
# =============================================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle("DeepSeek Workspace")
        self.resize(1220, 760)
        self._counter = 0

        # --- Сайдбар ---
        left_panel = QWidget()
        left_panel.setObjectName("Sidebar")
        left_panel.setFixedWidth(270)
        ll = QVBoxLayout(left_panel)
        ll.setContentsMargins(16, 20, 16, 16)
        ll.setSpacing(14)

        # Бренд
        brand_row = QHBoxLayout()
        brand_row.setSpacing(6)
        dot = QLabel("◆")
        dot.setObjectName("BrandAccent")
        brand = QLabel("DeepSeek")
        brand.setObjectName("Brand")
        brand_row.addWidget(dot)
        brand_row.addWidget(brand)
        brand_row.addStretch()
        ll.addLayout(brand_row)

        section = QLabel("РАБОЧИЕ СЕССИИ")
        section.setObjectName("Section")
        ll.addWidget(section)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.setStyleSheet("QListWidget { background: transparent; border: none; }")
        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        ll.addWidget(self.list_widget, stretch=1)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        self.add_button = QPushButton("+")
        self.add_button.setObjectName("IconBtn")
        self.add_button.setFixedHeight(38)
        self.add_button.setToolTip("Новая сессия")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.add_session)
        buttons_row.addWidget(self.add_button)

        self.remove_button = QPushButton("−")
        self.remove_button.setObjectName("IconBtn")
        self.remove_button.setFixedHeight(38)
        self.remove_button.setToolTip("Удалить сессию")
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.clicked.connect(self.remove_current_session)
        buttons_row.addWidget(self.remove_button)

        self.settings_button = QPushButton("⚙")
        self.settings_button.setObjectName("IconBtn")
        self.settings_button.setFixedHeight(38)
        self.settings_button.setToolTip("Настройки")
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.clicked.connect(self.open_settings)
        buttons_row.addWidget(self.settings_button)

        ll.addLayout(buttons_row)

        # --- Правая часть ---
        self.pages = QStackedWidget()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(left_panel)
        root.addWidget(self.pages, stretch=1)

        self.add_session()

    def add_session(self):
        self._counter += 1
        title = f"Сессия {self._counter}"
        page = WorkspacePage(title=title)
        page_index = self.pages.addWidget(page)

        item = QListWidgetItem(title)
        item.setData(Qt.UserRole, page_index)
        item.setSizeHint(QSize(0, 40))
        self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def remove_current_session(self):
        self.remove_session(self.list_widget.currentRow())

    def remove_session(self, row: int):
        if row < 0 or row >= self.list_widget.count():
            return
        if self.list_widget.count() <= 1:
            QMessageBox.information(self, "Информация", "Нельзя удалить последнюю сессию.")
            return

        item = self.list_widget.item(row)
        page_index = item.data(Qt.UserRole)
        widget = self.pages.widget(page_index)

        if getattr(widget, "_worker", None) is not None and widget._worker.isRunning():
            QMessageBox.information(self, "Информация", "Идёт запрос, дождитесь ответа.")
            self.list_widget.setCurrentRow(row)
            return

        self.list_widget.takeItem(row)
        self.pages.removeWidget(widget)
        widget.deleteLater()

    def on_row_changed(self, row: int):
        if row < 0:
            return
        item = self.list_widget.item(row)
        page_index = item.data(Qt.UserRole)
        self.pages.setCurrentIndex(page_index)

    def open_settings(self):
        cur = load_settings()
        dlg = SettingsDialog(
            mode='global',
            parent=self,
            values={
                'user_token': getattr(secret, 'USER_TOKEN', ''),
                'session_id': getattr(secret, 'DS_SESSION_ID', ''),
            },
        )
        if dlg.exec() == QDialog.Accepted:
            save_settings(cur)
            for i in range(self.pages.count()):
                w = self.pages.widget(i)
                if hasattr(w, 'apply_settings'):
                    w.apply_settings()

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is None:
            return
        row = self.list_widget.row(item)
        menu = QMenu(self)
        act = menu.addAction("Удалить сессию")
        act.triggered.connect(lambda: self.remove_session(row))
        menu.exec(self.list_widget.mapToGlobal(pos))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
