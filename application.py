import sys
import json
import os


import support
from main import DeepSeek_API
from support import prompt
import traceback

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QLabel, QStackedWidget, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QMenu,
    QDialog, QDialogButtonBox, QFormLayout, QSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal



try:
    import secret_local as secret
except ImportError:
    import secret_example as secret


# =============================================================
#  MessageWorker — фоновый запрос для on_enter
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
                self.answer_text.emit(support.extract(ans).get("text"))
                response = self._api.execute()
                if response[0] != "continue":
                    break
                self._text = f"{response[0]}: {response[1]}"
                self.answer.emit(self._text)
                #print(self._text)






        except Exception as e:
            self.error.emit(str(e))


# =============================================================
#  Настройки: файл + диалог
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


class SettingsDialog(QDialog):
    """Диалог настроек. scope — 'dash' или имя сессии (для заголовка)."""

    def __init__(self, parent=None, scope: str = "dash"):
        super().__init__(parent)
        self.setWindowTitle(f"Настройки — {scope}")
        self.resize(360, 220)

        self._settings = load_settings()

        form = QFormLayout()

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 600)
        self.timeout_spin.setValue(int(self._settings.get("api_timeout", 30)))
        form.addRow("Таймаут API (сек):", self.timeout_spin)

        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 500)
        self.steps_spin.setValue(int(self._settings.get("max_steps", 30)))
        form.addRow("Макс. шагов:", self.steps_spin)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 32)
        self.font_spin.setValue(int(self._settings.get("output_font_size", 12)))
        form.addRow("Размер шрифта вывода:", self.font_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def result_settings(self) -> dict:
        return {
            "api_timeout": self.timeout_spin.value(),
            "max_steps": self.steps_spin.value(),
            "output_font_size": self.font_spin.value(),
        }


# =============================================================
#  WorkspacePage — одна сессия
# =============================================================
class WorkspacePage(QWidget):
    def __init__(self, title: str = "Новая", parent=None):
        super().__init__(parent)
        self.title = title
        self.api = None
        self._worker = None
        self.msg_counter = 0

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_start_screen())   # 0 — Start
        self.stack.addWidget(self._build_main_screen())    # 1 — рабочий

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.apply_settings()

    # ---------- Экран 0: Start ----------
    def _build_start_screen(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)

        self.start_button = QPushButton("Start")
        self.start_button.setFixedSize(200, 60)
        self.start_button.setStyleSheet("font-size: 18px;")
        self.start_button.clicked.connect(self.on_start)

        self.start_status = QLabel("")
        self.start_status.setAlignment(Qt.AlignCenter)
        self.start_status.setStyleSheet("color: gray; font-size: 14px;")
        self.start_status.hide()

        layout.addStretch()
        layout.addWidget(self.start_button, alignment=Qt.AlignCenter)
        layout.addStretch()
        layout.addWidget(self.start_status, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        return screen

    # ---------- Экран 1: два поля ----------
    def _build_main_screen(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)

        # --- шапка сессии с кнопкой настроек ---
        header = QHBoxLayout()
        header.addWidget(QLabel(self.title))
        header.addStretch()
        self.session_settings_button = QPushButton("⚙ Настройки")
        self.session_settings_button.setToolTip("Настройки этой сессии")
        self.session_settings_button.clicked.connect(self.open_session_settings)
        header.addWidget(self.session_settings_button)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Ввод (Enter — выполнить):"))
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Введите текст и нажмите Enter...")
        self.entry.returnPressed.connect(self.on_enter)
        left_layout.addWidget(self.entry)
        left_layout.addStretch()

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        left_layout.addWidget(self.output_text)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Вывод:"))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        right_layout.addWidget(self.output)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        return screen

    # ---------- Настройки сессии ----------
    def open_session_settings(self):
        dlg = SettingsDialog(self, scope=self.title)
        if dlg.exec() == QDialog.Accepted:
            save_settings(dlg.result_settings())
            self.apply_settings()

    def apply_settings(self):
        s = load_settings()
        size = int(s.get("output_font_size", 12))
        # применяем только если экран уже построен
        if hasattr(self, "output") and self.output is not None:
            self.output.setStyleSheet(f"font-size: {size}px;")
        if hasattr(self, "output_text") and self.output_text is not None:
            self.output_text.setStyleSheet(f"font-size: {size}px;")

    # ---------- Start: блокирующий, без потока ----------
    def on_start(self):
        self.start_button.setEnabled(False)
        self.start_button.setText("Подключение...")
        self.start_status.setText("Запрос к API…")
        self.start_status.setStyleSheet("color: gray; font-size: 14px;")
        self.start_status.show()

        # принудительная перерисовка, чтобы статус был виден до запроса
        QApplication.processEvents()

        try:
            print(0)
            self.api = DeepSeek_API(
                secret.USER_TOKEN,
                secret.DS_SESSION_ID
            )
            self.api.creat_session()
            ans = self.api.send_message(prompt)
        except Exception as e:
            self.start_button.setEnabled(True)
            self.start_button.setText("Start")
            self.start_status.setText(f"Ошибка: {traceback.format_exc()}")
            self.start_status.setStyleSheet("color: red; font-size: 14px;")
            return

        # успех — только теперь переключаемся
        self.start_status.hide()
        self.start_button.setText("Start")
        self.stack.setCurrentIndex(1)
        self.output.append(ans)
        self.entry.setFocus()

    # ---------- Enter: с потоком ----------
    def on_enter(self):
        text = self.entry.text()
        if not text.strip():
            return
        if self._worker is not None and self._worker.isRunning():
            return

        self.entry.setEnabled(False)
        self.entry.setPlaceholderText("Ожидание ответа...")
        self.output.append(f">Пользователь:\n {text}:\n\n")
        self.output_text.append(f">Пользователь:\n {text}:\n\n")

        self._worker = MessageWorker(self.api, text, parent=self)
        self._worker.answer.connect(self._on_message_answer)
        self._worker.answer_text.connect(self._on_message_answer_text)
        self._worker.error.connect(self._on_message_error)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def _on_message_answer(self, ans: str):
        self.output.append(f">DeepSeek:\n {ans}\n")

    def _on_message_error(self, msg: str):
        self.output.append(f"> [Ошибка]:\n {msg}\n")

    def _on_message_answer_text(self, ans_text: str):
        self.msg_counter += 1
        if self.msg_counter <2:
            self.output_text.append(f">DeepSeek:\n {ans_text}\n")
        else:
            self.output_text.append(f"{ans_text}\n\n")

    def _cleanup_worker(self):
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self.msg_counter = 0
        self.output_text.append("\n\n")
        self.entry.setEnabled(True)
        self.entry.setPlaceholderText("Введите текст и нажмите Enter...")
        self.entry.clear()
        self.entry.setFocus()


# =============================================================
#  MainWindow — список слева + stacked справа
# =============================================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Список сессий + рабочий экран")
        self.resize(1000, 600)
        self._counter = 0

        # --- Левая панель ---
        left_panel = QWidget()
        left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        buttons_row = QHBoxLayout()

        self.add_button = QPushButton("+")
        self.add_button.setFixedSize(36, 28)
        self.add_button.setToolTip("Добавить сессию")
        self.add_button.clicked.connect(self.add_session)
        buttons_row.addWidget(self.add_button)

        self.remove_button = QPushButton("−")
        self.remove_button.setFixedSize(36, 28)
        self.remove_button.setToolTip("Удалить выбранную сессию")
        self.remove_button.clicked.connect(self.remove_current_session)
        buttons_row.addWidget(self.remove_button)

        self.settings_button = QPushButton("⚙")
        self.settings_button.setFixedSize(36, 28)
        self.settings_button.setToolTip("Настройки")
        self.settings_button.clicked.connect(self.open_settings)
        buttons_row.addWidget(self.settings_button)

        buttons_row.addStretch()
        left_layout.addLayout(buttons_row)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        left_layout.addWidget(self.list_widget)

        # --- Правая часть ---
        self.pages = QStackedWidget()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(left_panel)
        layout.addWidget(self.pages, stretch=1)

        self.add_session()

    # ---------- Добавление / удаление ----------
    def add_session(self):
        self._counter += 1
        title = f"Сессия {self._counter}"

        page = WorkspacePage(title=title)
        page_index = self.pages.addWidget(page)

        item = QListWidgetItem(title)
        item.setData(Qt.UserRole, page_index)
        self.list_widget.addItem(item)

        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def remove_current_session(self):
        self.remove_session(self.list_widget.currentRow())

    def remove_session(self, row: int):
        if row < 0 or row >= self.list_widget.count():
            return
        if self.list_widget.count() <= 1:
            QMessageBox.information(self, "Info", "Нельзя удалить последнюю сессию.")
            return

        item = self.list_widget.takeItem(row)
        page_index = item.data(Qt.UserRole)
        widget = self.pages.widget(page_index)

        # не даём удалить страницу, пока в ней идёт запрос
        if getattr(widget, "_worker", None) is not None and widget._worker.isRunning():
            QMessageBox.information(self, "Info", "Идёт запрос, дождитесь ответа.")
            # вернуть строку обратно
            self.list_widget.insertItem(row, item)
            self.list_widget.setCurrentRow(row)
            return

        self.pages.removeWidget(widget)
        widget.deleteLater()

    # ---------- Переключение / контекстное меню ----------
    def on_row_changed(self, row: int):
        if row < 0:
            return
        item = self.list_widget.item(row)
        page_index = item.data(Qt.UserRole)
        self.pages.setCurrentIndex(page_index)

    def open_settings(self):
        dlg = SettingsDialog(self, scope="dash-board")
        if dlg.exec() == QDialog.Accepted:
            save_settings(dlg.result_settings())
            # применить ко всем сессиям
            for i in range(self.pages.count()):
                w = self.pages.widget(i)
                if hasattr(w, "apply_settings"):
                    w.apply_settings()

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is None:
            return
        row = self.list_widget.row(item)

        menu = QMenu(self)
        act_delete = menu.addAction("Удалить сессию")
        act_delete.triggered.connect(lambda: self.remove_session(row))
        menu.exec(self.list_widget.mapToGlobal(pos))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
