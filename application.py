import sys

import secret
from main import DeepSeek_API
from support import prompt
import traceback

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QLabel, QStackedWidget, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal


# =============================================================
#  MessageWorker — фоновый запрос для on_enter
# =============================================================
class MessageWorker(QThread):
    answer = Signal(str)
    error = Signal(str)

    def __init__(self, api, text: str, parent=None):
        super().__init__(parent)
        self._api = api
        self._text = text

    def run(self):
        try:
            while True:
                ans = self._api.send_message(self._text)
                self.answer.emit(ans)
                response = self._api.execute()
                if response[0] != "continue":
                    break
                self._text = response[1]






        except Exception as e:
            self.error.emit(str(e))


# =============================================================
#  WorkspacePage — одна сессия
# =============================================================
class WorkspacePage(QWidget):
    def __init__(self, title: str = "Новая", parent=None):
        super().__init__(parent)
        self.title = title
        self.api = None
        self._worker = None

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_start_screen())   # 0 — Start
        self.stack.addWidget(self._build_main_screen())    # 1 — рабочий

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

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
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Ввод (Enter — выполнить):"))
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Введите текст и нажмите Enter...")
        self.entry.returnPressed.connect(self.on_enter)
        left_layout.addWidget(self.entry)
        left_layout.addStretch()

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
        self.output.append(f"> {text}:\n")

        self._worker = MessageWorker(self.api, text, parent=self)
        self._worker.answer.connect(self._on_message_answer)
        self._worker.error.connect(self._on_message_error)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def _on_message_answer(self, ans: str):
        self.output.append(f"> {ans}\n\n")

    def _on_message_error(self, msg: str):
        self.output.append(f"> [Ошибка] {msg}\n\n")

    def _cleanup_worker(self):
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
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