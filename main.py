import sys
import subprocess
import shutil
from pathlib import Path

from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.util import ClassNotFound
from pygments.token import Token

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QDir, QSettings
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QTextCharFormat,
    QSyntaxHighlighter,
    QKeySequence,
    QFileSystemModel,
    QTextFormat,
    QIcon,
)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPlainTextEdit,
    QSplitter, QTreeView, QVBoxLayout,
    QHBoxLayout, QLabel, QFileDialog, QMessageBox,
    QToolBar, QStatusBar, QFrame, QDialog, QComboBox,
    QFormLayout, QDialogButtonBox, QInputDialog,
    QCheckBox, QSpinBox, QTabWidget, QFontComboBox,
    QPushButton, QTextEdit
)
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView


APP_NAME = "MarkFlow"
PROJECT_ROOT = Path.home() / "Code/Projects/MarkFlow"
BUILD_DIR = PROJECT_ROOT / ".markflow" / "build"


# ============================================================
# MARKDOWN SYNTAX HIGHLIGHTER
# ============================================================

class MarkdownHighlighter(QSyntaxHighlighter):

    def __init__(self, document):
        super().__init__(document)
        self.set_theme("light")

    def set_theme(self, theme):
        self.rules = []

        colors = {
            "light": {
                "heading": "#245FC7",
                "bold": "#A15C00",
                "italic": "#9254B8",
                "code": "#287A52",
                "fence": "#16808A",
                "list": "#C04452",
                "link": "#087E9B",
                "quote": "#68758A",
                "table": "#A15C00",
            },
            "dark": {
                "heading": "#61AFEF",
                "bold": "#E5C07B",
                "italic": "#C678DD",
                "code": "#98C379",
                "fence": "#56B6C2",
                "list": "#E06C75",
                "link": "#56B6C2",
                "quote": "#ABB2BF",
                "table": "#D19A66",
            },
        }[theme]

        def add_rule(pattern, color, bold=False, italic=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            fmt.setFontWeight(
                QFont.Weight.Bold if bold else QFont.Weight.Normal
            )
            fmt.setFontItalic(italic)
            self.rules.append((pattern, fmt))

        add_rule(r"^#{1,6}\\s.*", colors["heading"], True)
        add_rule(r"\\*\\*.*?\\*\\*", colors["bold"], True)
        add_rule(r"\\*.*?\\*", colors["italic"], False, True)
        add_rule(r"`[^`]+`", colors["code"])
        add_rule(r"```.*", colors["fence"])
        add_rule(r"^\\s*[-*+]\\s", colors["list"], True)
        add_rule(r"^\\s*\\d+\\.\\s", colors["list"], True)
        add_rule(r"!\\[.*?\\]\\(.*?\\)", colors["link"])
        add_rule(r"\\[.*?\\]\\(.*?\\)", colors["link"])
        add_rule(r"^>\\s.*", colors["quote"], False, True)
        add_rule(r"^\\s*\\|.*\\|", colors["table"])

        self.rehighlight()

    def highlightBlock(self, text):
        import re
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(
                    match.start(),
                    match.end() - match.start(),
                    fmt
                )



# ============================================================
# PROGRAMMING LANGUAGE SYNTAX HIGHLIGHTER
# ============================================================

class PygmentsHighlighter(QSyntaxHighlighter):

    def __init__(self, document):
        super().__init__(document)

        self.lexer = TextLexer()
        self.theme = "light"
        self.formats = {}

        self._cached_text = None
        self._line_formats = []

        # Debounce full-document tokenization while the user is typing.
        self._highlight_timer = QTimer(self)
        self._highlight_timer.setSingleShot(True)
        self._highlight_timer.setInterval(180)
        self._highlight_timer.timeout.connect(self._refresh_highlighting)

        self.set_theme("light")

    def setDocument(self, document):
        super().setDocument(document)
        if document is not None and hasattr(self, "_highlight_timer"):
            self._highlight_timer.start(0)

    def _on_document_changed(self):
        # Refresh once after typing pauses, preserving multiline lexer state.
        if self.document() is not None:
            self._highlight_timer.start()

    def _refresh_highlighting(self):
        document = self.document()
        if document is None:
            return

        self._highlight_timer.stop()
        self._build_cache(document.toPlainText())
        self.rehighlight()

    def set_lexer_for_file(self, filename):
        filename = str(filename)
        suffix = Path(filename).suffix.lower()
        basename = Path(filename).name.lower()

        try:
            if basename == ".env" or basename.startswith(".env."):
                from pygments.lexers import get_lexer_by_name
                self.lexer = get_lexer_by_name("ini")

            elif basename == ".gitignore":
                self.lexer = TextLexer()

            else:
                self.lexer = get_lexer_for_filename(
                    filename,
                    stripnl=False,
                    ensurenl=False
                )

        except ClassNotFound:
            self.lexer = TextLexer()

        self._refresh_highlighting()

    def set_theme(self, theme):
        self.theme = theme

        if theme == "dark":
            colors = {
                "comment": "#7F8795",
                "docstring": "#829B83",
                "keyword": "#C678DD",
                "string": "#98C379",
                "string_escape": "#E5C07B",
                "number": "#D19A66",
                "function": "#61AFEF",
                "class": "#E5C07B",
                "type": "#56B6C2",
                "variable": "#E06C75",
                "constant": "#D19A66",
                "attribute": "#E5C07B",
                "namespace": "#56B6C2",
                "tag": "#E06C75",
                "builtin": "#56B6C2",
                "decorator": "#E5C07B",
                "operator": "#ABB2BF",
                "punctuation": "#ABB2BF",
            }
        else:
            colors = {
                "comment": "#7A8492",
                "docstring": "#547B58",
                "keyword": "#9254B8",
                "string": "#287A52",
                "string_escape": "#A15C00",
                "number": "#C04452",
                "function": "#245FC7",
                "class": "#A15C00",
                "type": "#087E9B",
                "variable": "#B13B50",
                "constant": "#A85B18",
                "attribute": "#986000",
                "namespace": "#087E9B",
                "tag": "#B13B50",
                "builtin": "#087E9B",
                "decorator": "#986000",
                "operator": "#526071",
                "punctuation": "#526071",
            }

        self.formats = {}

        for name, color in colors.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))

            if name in (
                "keyword",
                "function",
                "class",
                "type",
                "constant",
                "decorator",
                "tag",
            ):
                fmt.setFontWeight(QFont.Weight.Bold)

            if name in ("comment", "docstring"):
                fmt.setFontItalic(True)

            self.formats[name] = fmt

        self._refresh_highlighting()

    def _format_for_token(self, token):

        if token in Token.Comment:
            return self.formats["comment"]

        if token in Token.Keyword:
            return self.formats["keyword"]

        if token in Token.Literal.String.Doc:
            return self.formats["docstring"]

        if token in Token.Literal.String.Escape:
            return self.formats["string_escape"]

        if token in Token.Literal.String.Interpol:
            return self.formats["string_escape"]

        if token in Token.Literal.String:
            return self.formats["string"]

        if token in Token.Literal.Number:
            return self.formats["number"]

        if token in Token.Name.Decorator:
            return self.formats["decorator"]

        if token in Token.Name.Function:
            return self.formats["function"]

        if token in Token.Name.Class:
            return self.formats["class"]

        if token in Token.Name.Builtin:
            return self.formats["builtin"]

        if token in Token.Name.Constant:
            return self.formats["constant"]

        if token in Token.Name.Namespace:
            return self.formats["namespace"]

        if token in Token.Name.Attribute:
            return self.formats["attribute"]

        if token in Token.Name.Tag:
            return self.formats["tag"]

        if token in Token.Name.Variable:
            return self.formats["variable"]

        if token in Token.Name.Other:
            return self.formats["type"]

        if token in Token.Name:
            return self.formats["variable"]

        if token in Token.Operator:
            return self.formats["operator"]

        if token in Token.Punctuation:
            return self.formats["punctuation"]

        return None

    def _build_cache(self, text):
        """
        Tokenize the complete document.

        Keeping the full lexer input allows Pygments to correctly
        recognize multiline strings, comments and other constructs.
        Results are separated into Qt text blocks for fast rendering.
        """

        lines = [[] for _ in range(text.count("\n") + 1)]

        line_number = 0
        column = 0

        for _, token, value in self.lexer.get_tokens_unprocessed(text):
            fmt = self._format_for_token(token)

            parts = value.split("\n")

            for index, part in enumerate(parts):

                if part and fmt is not None:
                    lines[line_number].append(
                        (column, len(part), fmt)
                    )

                column += len(part)

                if index < len(parts) - 1:
                    line_number += 1
                    column = 0

        self._line_formats = lines
        self._cached_text = text

    def highlightBlock(self, text):
        try:
            # Cache is prepared once before rehighlight(), not once per block.
            block_number = self.currentBlock().blockNumber()

            if block_number >= len(self._line_formats):
                return

            for position, length, fmt in self._line_formats[block_number]:
                self.setFormat(position, length, fmt)

        except Exception:
            # Syntax highlighting must never interrupt editing.
            return


# ============================================================
# GENERAL TEXT EDITOR
# ============================================================

class TextEditor(QPlainTextEdit):

    def __init__(
        self,
        font_family="JetBrains Mono",
        font_size=11,
        tab_width=4,
        word_wrap=True,
        current_line=True,
        syntax_highlighting=True
    ):
        super().__init__()

        self.setPlaceholderText(
            "# Welcome to MarkFlow\\n\\n"
            "Start writing your Markdown document here..."
        )

        self.current_theme = "light"

        self.markdown_highlighter = MarkdownHighlighter(
            self.document()
        )
        self.code_highlighter = PygmentsHighlighter(
            self.document()
        )

        # Content changes invalidate the full-document token cache.
        # Formatting changes do not emit this editor signal.
        self.textChanged.connect(
            self.code_highlighter._on_document_changed
        )

        self.active_language = "markdown"

        self.apply_editor_settings(
            font_family,
            font_size,
            tab_width,
            word_wrap,
            current_line,
            syntax_highlighting
        )
        self.apply_theme("light")

        self.cursorPositionChanged.connect(self.highlight_current_line)

    def apply_editor_settings(
        self,
        font_family,
        font_size,
        tab_width,
        word_wrap,
        current_line,
        syntax_highlighting
    ):
        self.editor_font_family = font_family
        self.show_current_line = current_line
        self.syntax_enabled = syntax_highlighting

        self.setFont(QFont(font_family, int(font_size)))
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * int(tab_width)
        )

        mode = (
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if word_wrap
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.setLineWrapMode(mode)

        self.set_syntax_highlighting(syntax_highlighting)

        self.highlight_current_line()

    def set_language(self, filename):
        suffix = Path(str(filename)).suffix.lower()

        if suffix in (".md", ".markdown") or not suffix:
            self.active_language = "markdown"
            self.code_highlighter.setDocument(None)
            self.markdown_highlighter.setDocument(self.document())
        else:
            self.active_language = "code"
            self.markdown_highlighter.setDocument(None)
            self.code_highlighter.set_lexer_for_file(filename)
            self.code_highlighter.setDocument(self.document())

        self.set_syntax_highlighting(self.syntax_enabled)

    def set_syntax_highlighting(self, enabled):
        self.syntax_enabled = bool(enabled)

        self.markdown_highlighter.setDocument(None)
        self.code_highlighter.setDocument(None)

        if self.syntax_enabled:
            if self.active_language == "markdown":
                self.markdown_highlighter.setDocument(self.document())
            else:
                self.code_highlighter.setDocument(self.document())

    def highlight_current_line(self):
        if not self.show_current_line or not self.isEnabled():
            self.setExtraSelections([])
            return

        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(
            QColor("#F1F4FA" if self.current_theme == "light" else "#292F3A")
        )
        selection.format.setProperty(
            QTextFormat.Property.FullWidthSelection, True
        )
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()

        self.setExtraSelections([selection])

    def apply_theme(self, theme):
        self.current_theme = theme
        if theme == "light":
            background = "#FFFFFF"
            foreground = "#263247"
            selection = "#DCE8FF"
        else:
            background = "#1E232B"
            foreground = "#D5DAE3"
            selection = "#39465B"

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {background};
                color: {foreground};
                border: none;
                padding: 18px;
                selection-background-color: {selection};
                selection-color: {foreground};
            }}
        """)
        self.markdown_highlighter.set_theme(theme)
        self.code_highlighter.set_theme(theme)
        self.highlight_current_line()


# ============================================================
# BACKGROUND PDF COMPILER
# ============================================================

class CompileWorker(QThread):

    completed = pyqtSignal(bool, str)

    def __init__(self, markdown_path, pdf_path, resource_paths):
        super().__init__()

        self.markdown_path = Path(markdown_path)
        self.pdf_path = Path(pdf_path)
        self.resource_paths = resource_paths

    def run(self):

        command = [
            "pandoc",
            str(self.markdown_path),
            "--from=markdown+tex_math_dollars+raw_tex",
            "--standalone",
            "--pdf-engine=xelatex",
            "-o",
            str(self.pdf_path),
        ]

        for resource in self.resource_paths:
            command.append(f"--resource-path={resource}")

        try:
            result = subprocess.run(
                command,
                cwd=str(self.markdown_path.parent),
                capture_output=True,
                text=True,
                timeout=180
            )

            if result.returncode == 0:
                self.completed.emit(True, "PDF compiled successfully.")
            else:
                error = result.stderr or result.stdout
                self.completed.emit(False, error[-6000:])

        except subprocess.TimeoutExpired:
            self.completed.emit(False, "PDF compilation timed out.")

        except Exception as exc:
            self.completed.emit(False, str(exc))


# ============================================================
# MAIN APPLICATION
# ============================================================

class MarkFlow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.current_file = None
        self.settings = QSettings("DynaIO", "MarkFlow")

        default_workspace = Path.home() / "Documents"
        if not default_workspace.is_dir():
            default_workspace = Path.home()

        saved_workspace = self.settings.value(
            "workspace/folder", str(default_workspace)
        )
        workspace = Path(str(saved_workspace)).expanduser()
        if not workspace.is_dir():
            workspace = default_workspace

        self.project_root = workspace.resolve()
        self.settings.setValue("workspace/folder", str(self.project_root))
        self.markdown_only_filter = self.settings.value(
            "explorer/markdown_only", True, type=bool
        )
        self.build_dir = self.project_root / ".markflow" / "build"
        self.theme = str(self.settings.value("theme", "light")).lower()
        if self.theme not in ("light", "dark"):
            self.theme = "light"

        self.editor_font_family = self.settings.value(
            "editor/font_family", "JetBrains Mono"
        )
        self.editor_font_size = self.settings.value(
            "editor/font_size", 11, type=int
        )
        self.tab_width = self.settings.value(
            "editor/tab_width", 4, type=int
        )
        self.word_wrap = self.settings.value(
            "editor/word_wrap", True, type=bool
        )
        self.current_line_highlight = self.settings.value(
            "editor/current_line", True, type=bool
        )
        self.syntax_highlighting = self.settings.value(
            "markdown/syntax_highlighting", True, type=bool
        )
        self.auto_compile = self.settings.value(
            "markdown/auto_compile", True, type=bool
        )
        self.compile_delay = self.settings.value(
            "markdown/compile_delay", 800, type=int
        )
        self.ui_font_size = self.settings.value(
            "appearance/ui_font_size", 10, type=int
        )

        self.preview_preferred_visible = self.settings.value(
            "view/pdf_preview", True, type=bool
        )
        self.preview_is_visible = self.preview_preferred_visible

        self.pdf_document = None
        self.worker = None
        self.compile_pending = False

        self.setWindowTitle("MarkFlow")
        self.resize(1500, 900)
        self.setMinimumSize(1000, 650)

        self.build_dir.mkdir(parents=True, exist_ok=True)

        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_shortcuts()
        self.setup_timers()

        self.statusBar().showMessage("Ready")

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # FILE EXPLORER

        self.file_model = QFileSystemModel()
        self.file_model.setFilter(
            QDir.Filter.AllDirs |
            QDir.Filter.Files |
            QDir.Filter.NoDotAndDotDot
        )
        self.file_model.setNameFilterDisables(False)
        self.file_model.setNameFilters(
            ["*.md", "*.markdown"] if self.markdown_only_filter else []
        )

        self.file_model.setRootPath(str(self.project_root))

        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(
            self.file_model.index(str(self.project_root))
        )

        self.file_tree.setHeaderHidden(True)

        for column in range(1, 4):
            self.file_tree.hideColumn(column)

        self.file_tree.setMinimumWidth(150)
        self.file_tree.doubleClicked.connect(self.on_file_double_clicked)

        explorer_container = QWidget()
        explorer_layout = QVBoxLayout(explorer_container)
        explorer_layout.setContentsMargins(8, 8, 8, 8)

        self.explorer_title = QLabel(f"  EXPLORER  |  {self.project_root.name}")
        self.explorer_title.setObjectName("panelTitle")

        explorer_layout.addWidget(self.explorer_title)

        self.markdown_filter_checkbox = QCheckBox("Markdown files only")
        self.markdown_filter_checkbox.setChecked(
            self.markdown_only_filter
        )
        self.markdown_filter_checkbox.toggled.connect(
            self.set_markdown_filter
        )
        explorer_layout.addWidget(self.markdown_filter_checkbox)
        explorer_layout.addWidget(self.file_tree)

        # MARKDOWN EDITOR

        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self.editor_title = QLabel("  EDITOR  |  Untitled.md")
        self.editor_title.setObjectName("panelTitle")

        self.editor = TextEditor(
            self.editor_font_family,
            self.editor_font_size,
            self.tab_width,
            self.word_wrap,
            self.current_line_highlight,
            self.syntax_highlighting
        )

        editor_layout.addWidget(self.editor_title)
        editor_layout.addWidget(self.editor)

        # PDF PREVIEW

        preview_container = QWidget()
        self.preview_container = preview_container
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        preview_title = QLabel("  PDF PREVIEW")
        preview_title.setObjectName("panelTitle")

        self.pdf_view = QPdfView(self)
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.pdf_view)

        # SPLITTERS

        self.editor_preview_splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        self.editor_preview_splitter.addWidget(editor_container)
        self.editor_preview_splitter.addWidget(preview_container)

        self.editor_preview_splitter.setSizes(
            [600, 600] if self.preview_preferred_visible else [1200, 0]
        )
        self.preview_container.setVisible(self.preview_preferred_visible)

        main_splitter.addWidget(explorer_container)
        main_splitter.addWidget(self.editor_preview_splitter)

        main_splitter.setSizes([220, 1280])

        main_layout.addWidget(main_splitter)

        # COMPILATION STATUS

        self.compilation_label = QLabel("● Ready")
        self.compilation_label.setObjectName("statusLabel")

        self.statusBar().addPermanentWidget(self.compilation_label)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #282C34;
                color: #ABB2BF;
            }

            QLabel#panelTitle {
                background-color: #21252B;
                color: #61AFEF;
                padding: 11px;
                font-weight: bold;
                font-size: 10px;
                border-bottom: 1px solid #181A1F;
            }

            QLabel#statusLabel {
                color: #98C379;
                padding: 0 12px;
            }

            QTreeView {
                background-color: #21252B;
                color: #ABB2BF;
                border: none;
                outline: none;
            }

            QTreeView::item {
                padding: 5px;
            }

            QTreeView::item:selected {
                background-color: #3E4451;
            }

            QToolBar {
                background-color: #21252B;
                border: none;
                spacing: 7px;
                padding: 5px;
            }

            QToolButton {
                color: #ABB2BF;
                padding: 6px 10px;
            }

            QToolButton:hover {
                background-color: #3E4451;
            }

            QStatusBar {
                background-color: #21252B;
                color: #ABB2BF;
            }

            QSplitter::handle {
                background-color: #181A1F;
                width: 3px;
            }
        """)

        self.apply_theme(self.theme)

    # --------------------------------------------------------
    # THEMES AND SETTINGS
    # --------------------------------------------------------

    def apply_theme(self, theme):
        self.theme = theme
        self.settings.setValue("theme", theme)

        if theme == "light":
            c = {
                "window": "#F3F5F9",
                "panel": "#FFFFFF",
                "editor": "#FFFFFF",
                "text": "#263247",
                "muted": "#697586",
                "border": "#E1E6EF",
                "accent": "#356AE6",
                "hover": "#EAF0FC",
                "selected": "#DCE8FF",
                "status": "#F8FAFD",
            }
        else:
            c = {
                "window": "#20252D",
                "panel": "#282E38",
                "editor": "#1E232B",
                "text": "#D5DAE3",
                "muted": "#A0A9B8",
                "border": "#373F4B",
                "accent": "#70A5F5",
                "hover": "#343D4B",
                "selected": "#39465B",
                "status": "#282E38",
            }

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {c["window"]};
                color: {c["text"]};
                font-size: {self.ui_font_size}pt;
            }}
            QMenuBar {{
                background: {c["panel"]};
                color: {c["text"]};
                border-bottom: 1px solid {c["border"]};
                padding: 5px;
            }}
            QMenuBar::item {{
                padding: 6px 10px;
                border-radius: 5px;
            }}
            QMenuBar::item:selected, QMenu::item:selected {{
                background: {c["hover"]};
            }}
            QMenu {{
                background: {c["panel"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                padding: 5px;
            }}
            QMenu::item {{
                padding: 7px 25px 7px 12px;
                border-radius: 4px;
            }}
            QLabel#panelTitle {{
                background: {c["panel"]};
                color: {c["accent"]};
                padding: 12px 10px;
                font-size: 9pt;
                font-weight:  bold;
                border-bottom: 1px solid {c["border"]};
            }}
            QLabel#statusLabel {{
                color: {c["accent"]};
                padding: 0 12px;
            }}
            QTreeView {{
                background: {c["panel"]};
                color: {c["text"]};
                border: none;
                outline: none;
                padding: 5px;
            }}
            QTreeView::item {{
                padding: 6px 4px;
                border-radius: 4px;
            }}
            QTreeView::item:hover {{
                background: {c["hover"]};
            }}
            QTreeView::item:selected {{
                background: {c["selected"]};
                color: {c["text"]};
            }}
            QToolBar {{
                background: {c["panel"]};
                border: none;
                border-bottom: 1px solid {c["border"]};
                spacing: 7px;
                padding: 7px;
            }}
            QToolButton {{
                background: transparent;
                color: {c["text"]};
                padding: 7px 11px;
                border-radius: 5px;
            }}
            QToolButton:hover {{
                background: {c["hover"]};
            }}
            QStatusBar {{
                background: {c["status"]};
                color: {c["muted"]};
                border-top: 1px solid {c["border"]};
            }}
            QSplitter::handle {{
                background: {c["border"]};
                width: 3px;
            }}
            QPushButton {{
                background: {c["accent"]};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 7px 15px;
            }}
            QPushButton:hover {{
                background: {c["accent"]};
            }}
            QComboBox, QLineEdit {{
                background: {c["panel"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 5px;
                padding: 6px;
            }}
        """)

        self.editor.apply_theme(theme)

    def open_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("MarkFlow Settings")
        dialog.setMinimumSize(560, 480)

        root = QVBoxLayout(dialog)
        tabs = QTabWidget()
        root.addWidget(tabs)

        # EDITOR TAB
        editor_tab = QWidget()
        editor_form = QFormLayout(editor_tab)
        editor_form.setContentsMargins(18, 18, 18, 18)
        editor_form.setSpacing(14)

        font_family = QFontComboBox()
        font_family.setCurrentFont(QFont(self.editor_font_family))

        font_size = QSpinBox()
        font_size.setRange(8, 32)
        font_size.setValue(self.editor_font_size)
        font_size.setSuffix(" pt")

        tab_width = QSpinBox()
        tab_width.setRange(2, 8)
        tab_width.setValue(self.tab_width)
        tab_width.setSuffix(" spaces")

        word_wrap = QCheckBox("Wrap long lines")
        word_wrap.setChecked(self.word_wrap)

        current_line = QCheckBox("Highlight current line")
        current_line.setChecked(self.current_line_highlight)

        editor_form.addRow("Font family:", font_family)
        editor_form.addRow("Font size:", font_size)
        editor_form.addRow("Tab width:", tab_width)
        editor_form.addRow("", word_wrap)
        editor_form.addRow("", current_line)

        tabs.addTab(editor_tab, "Editor")

        # MARKDOWN TAB
        markdown_tab = QWidget()
        markdown_form = QFormLayout(markdown_tab)
        markdown_form.setContentsMargins(18, 18, 18, 18)
        markdown_form.setSpacing(14)

        syntax = QCheckBox("Enable Markdown syntax highlighting")
        syntax.setChecked(self.syntax_highlighting)

        auto_compile = QCheckBox(
            "Automatically compile PDF when document changes"
        )
        auto_compile.setChecked(self.auto_compile)

        compile_delay = QSpinBox()
        compile_delay.setRange(200, 5000)
        compile_delay.setSingleStep(100)
        compile_delay.setValue(self.compile_delay)
        compile_delay.setSuffix(" ms")
        compile_delay.setEnabled(self.auto_compile)

        auto_compile.toggled.connect(compile_delay.setEnabled)

        markdown_form.addRow("", syntax)
        markdown_form.addRow("", auto_compile)
        markdown_form.addRow("Compilation delay:", compile_delay)

        tabs.addTab(markdown_tab, "Markdown")

        # APPEARANCE TAB
        appearance_tab = QWidget()
        appearance_form = QFormLayout(appearance_tab)
        appearance_form.setContentsMargins(18, 18, 18, 18)
        appearance_form.setSpacing(14)

        theme = QComboBox()
        theme.addItem("Light", "light")
        theme.addItem("Dark", "dark")
        theme.setCurrentIndex(0 if self.theme == "light" else 1)

        ui_font_size = QSpinBox()
        ui_font_size.setRange(8, 16)
        ui_font_size.setValue(self.ui_font_size)
        ui_font_size.setSuffix(" pt")

        appearance_form.addRow("Application theme:", theme)
        appearance_form.addRow("Interface font size:", ui_font_size)

        tabs.addTab(appearance_tab, "Appearance")

        # BUTTONS
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )

        reset_button = buttons.addButton(
            "Reset to Defaults",
            QDialogButtonBox.ButtonRole.ResetRole
        )

        def reset_defaults():
            theme.setCurrentIndex(0)
            font_family.setCurrentFont(QFont("JetBrains Mono"))
            font_size.setValue(11)
            tab_width.setValue(4)
            word_wrap.setChecked(True)
            current_line.setChecked(True)
            syntax.setChecked(True)
            auto_compile.setChecked(True)
            compile_delay.setValue(800)
            ui_font_size.setValue(10)

        reset_button.clicked.connect(reset_defaults)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        root.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Apply and persist
        self.theme = theme.currentData()
        self.editor_font_family = font_family.currentFont().family()
        self.editor_font_size = font_size.value()
        self.tab_width = tab_width.value()
        self.word_wrap = word_wrap.isChecked()
        self.current_line_highlight = current_line.isChecked()
        self.syntax_highlighting = syntax.isChecked()
        self.auto_compile = auto_compile.isChecked()
        self.compile_delay = compile_delay.value()
        self.ui_font_size = ui_font_size.value()

        values = {
            "theme": self.theme,
            "editor/font_family": self.editor_font_family,
            "editor/font_size": self.editor_font_size,
            "editor/tab_width": self.tab_width,
            "editor/word_wrap": self.word_wrap,
            "editor/current_line": self.current_line_highlight,
            "markdown/syntax_highlighting": self.syntax_highlighting,
            "markdown/auto_compile": self.auto_compile,
            "markdown/compile_delay": self.compile_delay,
            "appearance/ui_font_size": self.ui_font_size,
        }

        for key, value in values.items():
            self.settings.setValue(key, value)

        self.settings.sync()

        self.apply_theme(self.theme)
        self.editor.apply_editor_settings(
            self.editor_font_family,
            self.editor_font_size,
            self.tab_width,
            self.word_wrap,
            self.current_line_highlight,
            self.syntax_highlighting
        )
        self.update_document_mode()
        self.compile_timer.setInterval(self.compile_delay)

        if (
            self.is_markdown_document()
            and self.auto_compile
            and self.editor.document().isModified()
        ):
            self.compile_timer.start()
        else:
            self.compile_timer.stop()

        self.statusBar().showMessage("Settings saved", 3000)

    # --------------------------------------------------------
    # FIND AND REPLACE
    # --------------------------------------------------------

    def find_text(self):
        text, accepted = QInputDialog.getText(
            self, "Find", "Find text:"
        )
        if accepted and text:
            if not self.editor.find(text):
                self.editor.moveCursor(
                    self.editor.textCursor().MoveOperation.Start
                )
                if not self.editor.find(text):
                    QMessageBox.information(
                        self, "Find", "No matching text was found."
                    )

    def replace_text(self):
        old, accepted = QInputDialog.getText(
            self, "Replace", "Find:"
        )
        if not accepted or not old:
            return

        new, accepted = QInputDialog.getText(
            self, "Replace", "Replace with:"
        )
        if not accepted:
            return

        content = self.editor.toPlainText()
        count = content.count(old)
        if count:
            self.editor.setPlainText(content.replace(old, new))
            self.statusBar().showMessage(
                f"Replaced {count} occurrence(s)."
            )
        else:
            QMessageBox.information(
                self, "Replace", "No matching text was found."
            )

    # --------------------------------------------------------
    # MENUS
    # --------------------------------------------------------

    def setup_menus(self):

        file_menu = self.menuBar().addMenu("File")

        self.add_action(file_menu, "New", self.new_file, "Ctrl+N")
        self.add_action(file_menu, "Open", self.open_file, "Ctrl+O")
        self.add_action(file_menu, "Open Workspace Folder...",
                        self.open_project_folder)
        self.add_action(file_menu, "Save", self.save_file, "Ctrl+S")
        self.add_action(file_menu, "Save As", self.save_file_as,
                        "Ctrl+Shift+S")

        file_menu.addSeparator()

        self.export_action = self.add_action(
            file_menu, "Export PDF", self.export_pdf, "Ctrl+E"
        )

        file_menu.addSeparator()

        self.add_action(file_menu, "Exit", self.close, "Ctrl+Q")

        edit_menu = self.menuBar().addMenu("Edit")

        self.add_action(edit_menu, "Undo", self.editor.undo, "Ctrl+Z")
        self.add_action(edit_menu, "Redo", self.editor.redo, "Ctrl+Y")
        self.add_action(edit_menu, "Select All",
                        self.editor.selectAll, "Ctrl+A")
        edit_menu.addSeparator()
        self.add_action(edit_menu, "Find...", self.find_text, "Ctrl+F")
        self.add_action(edit_menu, "Replace...", self.replace_text, "Ctrl+H")
        edit_menu.addSeparator()
        self.add_action(edit_menu, "Settings...", self.open_settings)

        view_menu = self.menuBar().addMenu("View")

        self.compile_action = self.add_action(
            view_menu, "Compile PDF", self.compile_document, "F5"
        )

        self.preview_action = self.add_action(
            view_menu, "Show PDF Preview",
            lambda: self.toggle_pdf_preview(), "Ctrl+Shift+P"
        )
        self.preview_action.setCheckable(True)
        self.preview_action.setChecked(self.preview_is_visible)

        self.add_action(view_menu, "Editor Only",
                        self.show_editor_only)
        self.add_action(view_menu, "PDF Only",
                        self.show_pdf_only)
        self.add_action(view_menu, "Split View",
                        self.show_split_view)

        help_menu = self.menuBar().addMenu("Help")

        self.add_action(help_menu, "About MarkFlow", self.about)

    def add_action(self, menu, title, callback, shortcut=None):

        action = QAction(title, self)
        action.triggered.connect(callback)

        if shortcut:
            action.setShortcut(QKeySequence(shortcut))

        menu.addAction(action)
        return action

    # --------------------------------------------------------
    # TOOLBAR
    # --------------------------------------------------------

    def setup_toolbar(self):

        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        actions = [
            ("New", self.new_file),
            ("Open", self.open_file),
            ("Save", self.save_file),
            ("Export PDF", self.export_pdf),
            ("Compile", self.compile_document),
        ]

        for title, callback in actions:
            action = QAction(title, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)

    def setup_shortcuts(self):
        pass

    # --------------------------------------------------------
    # TIMERS
    # --------------------------------------------------------

    def setup_timers(self):

        self.compile_timer = QTimer(self)
        self.compile_timer.setSingleShot(True)
        self.compile_timer.setInterval(self.compile_delay)
        self.compile_timer.timeout.connect(self.compile_document)

        self.editor.textChanged.connect(self.on_text_changed)

    def on_text_changed(self):

        if not self.is_markdown_document():
            self.compilation_label.setText("● Text modified")
            self.compilation_label.setStyleSheet("color: #61AFEF")
            self.compile_timer.stop()
            return

        self.compilation_label.setText("● Changes detected")
        self.compilation_label.setStyleSheet("color: #E5C07B")

        if self.auto_compile:
            self.compile_timer.start()

    # --------------------------------------------------------
    # FILE OPERATIONS
    # --------------------------------------------------------

    def new_file(self):

        self.current_file = None
        self.editor.clear()
        self.editor_title.setText("  EDITOR  |  Untitled.md")
        self.update_document_mode()
        self.statusBar().showMessage("New Markdown document")

    def open_file(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Text File",
            str(self.project_root),
            "Text files (*.txt *.md *.markdown *.py *.json *.yaml *.yml "
            "*.xml *.html *.htm *.css *.js *.ts *.jsx *.tsx *.sh "
            "*.c *.cpp *.h *.hpp *.java *.dart *.sql *.toml *.ini "
            "*.cfg *.csv *.log *.rst *.tex);;All files (*)"
        )

        if path:
            self.load_file(path)

    def is_markdown_document(self):
        if self.current_file is None:
            return True
        return self.current_file.suffix.lower() in (".md", ".markdown")

    def update_document_mode(self):
        is_markdown = self.is_markdown_document()

        # Select Markdown or programming-language highlighting.
        # Unknown extensions automatically use plain text.
        self.editor.set_language(
            self.current_file or Path("Untitled.md")
        )
        self.editor.set_syntax_highlighting(
            self.syntax_highlighting
        )

        # The PDF preview is only available for Markdown documents.
        self.preview_container.setVisible(
            is_markdown and self.preview_preferred_visible
        )
        self.preview_is_visible = (
            is_markdown and self.preview_preferred_visible
        )

        if is_markdown:
            if self.preview_preferred_visible:
                self.editor_preview_splitter.setSizes([600, 600])

            self.compilation_label.setText("● Markdown mode")
            self.compilation_label.setStyleSheet("color: #98C379")
            self.statusBar().showMessage("Markdown document ready")
        else:
            self.compile_timer.stop()
            self.compile_pending = False

            self.compilation_label.setText("● Text mode")
            self.compilation_label.setStyleSheet("color: #61AFEF")
            self.statusBar().showMessage(
                "Text editing mode — PDF compilation is unavailable"
            )

        if hasattr(self, "compile_action"):
            self.compile_action.setEnabled(is_markdown)
        if hasattr(self, "export_action"):
            self.export_action.setEnabled(is_markdown)
        if hasattr(self, "preview_action"):
            self.preview_action.setEnabled(is_markdown)
            self.preview_action.setChecked(self.preview_is_visible)

    def load_file(self, path):

        try:
            path = Path(path)
            content = path.read_text(encoding="utf-8")

            self.current_file = path

            self.editor.blockSignals(True)
            self.editor.setPlainText(content)
            self.editor.blockSignals(False)

            self.editor.document().setModified(False)

            self.editor_title.setText(
                f"  EDITOR  |  {path.name}"
            )

            self.statusBar().showMessage(f"Opened {path}")

            self.update_document_mode()

            if self.is_markdown_document():
                self.compile_document()

        except Exception as exc:
            QMessageBox.critical(self, "Open Error", str(exc))

    def save_file(self):

        if self.current_file is None:
            self.save_file_as()
            return

        try:
            self.current_file.write_text(
                self.editor.toPlainText(),
                encoding="utf-8"
            )

            self.editor.document().setModified(False)
            self.statusBar().showMessage("File saved")

        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def save_file_as(self):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Text File",
            str(
                self.current_file
                if self.current_file
                else self.project_root / "Untitled.md"
            ),
            "All files (*)"
        )

        if path:
            self.current_file = Path(path)
            self.save_file()

            self.editor_title.setText(
                f"  EDITOR  |  {self.current_file.name}"
            )
            self.update_document_mode()

    def set_markdown_filter(self, enabled):

        self.markdown_only_filter = bool(enabled)
        self.file_model.setNameFilters(
            ["*.md", "*.markdown"] if enabled else []
        )
        self.settings.setValue("explorer/markdown_only", bool(enabled))
        self.settings.sync()
        self.statusBar().showMessage(
            "Showing Markdown files only" if enabled
            else "Showing all files"
        )

    def open_project_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Open Workspace Folder",
            str(self.project_root)
        )

        if folder:
            self.project_root = Path(folder).expanduser().resolve()
            self.settings.setValue(
                "workspace/folder", str(self.project_root)
            )
            self.settings.sync()
            self.build_dir = self.project_root / ".markflow" / "build"
            self.build_dir.mkdir(parents=True, exist_ok=True)

            root_index = self.file_model.setRootPath(
                str(self.project_root)
            )
            self.file_tree.setRootIndex(root_index)
            self.explorer_title.setText(
                f"  EXPLORER  |  {self.project_root.name}"
            )
            self.statusBar().showMessage(f"Project: {folder}")

    def on_file_double_clicked(self, index):

        path = Path(self.file_model.filePath(index))

        if path.is_file():
            self.load_file(path)

    # --------------------------------------------------------
    # PDF COMPILATION
    # --------------------------------------------------------

    def compile_document(self):

        if not self.is_markdown_document():
            self.compile_timer.stop()
            return

        if self.worker is not None and self.worker.isRunning():
            self.compile_pending = True
            return

        required_tools = {
            "pandoc": "pandoc",
            "xelatex": "texlive-xetex",
            "rsvg-convert": "librsvg2-bin",
        }
        missing_tools = [
            (command, package)
            for command, package in required_tools.items()
            if shutil.which(command) is None
        ]

        if missing_tools:
            details = "\n".join(
                f"• {command} — install with: sudo apt install {package}"
                for command, package in missing_tools
            )
            self.compilation_label.setText("● Missing PDF dependencies")
            self.compilation_label.setStyleSheet("color: #E06C75")
            self.statusBar().showMessage(
                "PDF compilation dependencies are missing"
            )
            QMessageBox.warning(
                self,
                "Missing PDF Dependencies",
                "MarkFlow cannot compile this document because required tools "
                "are missing:\n\n" + details,
            )
            return

        content = self.editor.toPlainText()

        if not content.strip():
            self.compilation_label.setText("● Empty document")
            return

        self.build_dir.mkdir(parents=True, exist_ok=True)

        source = self.build_dir / "preview.md"
        pdf = self.build_dir / "preview.pdf"

        source.write_text(content, encoding="utf-8")

        resource_paths = [str(self.project_root)]

        if self.current_file:
            resource_paths.insert(0, str(self.current_file.parent))

        self.compilation_label.setText("● Compiling...")
        self.compilation_label.setStyleSheet("color: #E5C07B")

        self.statusBar().showMessage("Generating PDF...")

        self.worker = CompileWorker(
            source,
            pdf,
            resource_paths
        )

        self.worker.completed.connect(
            lambda success, message: self.on_compilation_finished(
                success, message, pdf
            )
        )

        self.worker.start()

    def on_compilation_finished(self, success, message, pdf):

        if not self.is_markdown_document():
            self.compile_pending = False
            return

        if success:

            self.reload_pdf(pdf)

            self.compilation_label.setText("● PDF Updated")
            self.compilation_label.setStyleSheet("color: #98C379")

            self.statusBar().showMessage(message)

        else:

            self.compilation_label.setText("● Compilation Error")
            self.compilation_label.setStyleSheet("color: #E06C75")

            self.statusBar().showMessage("PDF compilation failed")

            QMessageBox.warning(
                self,
                "Compilation Error",
                message
            )

        if self.compile_pending:
            self.compile_pending = False
            self.compile_timer.start(200)

    # --------------------------------------------------------
    # PDF VIEWER
    # --------------------------------------------------------

    def reload_pdf(self, path):

        new_document = QPdfDocument(self)
        new_document.load(str(path))

        self.pdf_view.setDocument(new_document)

        old_document = self.pdf_document
        self.pdf_document = new_document

        if old_document:
            old_document.deleteLater()

    def export_pdf(self):

        if not self.is_markdown_document():
            QMessageBox.information(
                self,
                "Export PDF",
                "PDF export is available for Markdown documents only."
            )
            return

        source = self.build_dir / "preview.pdf"

        if not source.exists():
            QMessageBox.information(
                self,
                "Export PDF",
                "Compile the document first."
            )
            return

        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            str(self.project_root / "document.pdf"),
            "PDF (*.pdf)"
        )

        if destination:
            import shutil
            shutil.copy2(source, destination)
            self.statusBar().showMessage("PDF exported successfully")

    # --------------------------------------------------------
    # VIEW MODES
    # --------------------------------------------------------

    def toggle_pdf_preview(self):
        if not self.is_markdown_document():
            return

        self.preview_preferred_visible = not self.preview_preferred_visible
        self.preview_is_visible = self.preview_preferred_visible

        self.settings.setValue(
            "view/pdf_preview", self.preview_preferred_visible
        )

        self.preview_container.setVisible(self.preview_is_visible)

        if self.preview_is_visible:
            self.editor_preview_splitter.setSizes([600, 600])
        else:
            self.editor_preview_splitter.setSizes([1200, 0])

        if hasattr(self, "preview_action"):
            self.preview_action.setChecked(self.preview_is_visible)

    def show_editor_only(self):
        if not self.is_markdown_document():
            return
        self.preview_container.setVisible(True)
        self.preview_is_visible = True
        self.editor_preview_splitter.setSizes([1200, 0])

    def show_pdf_only(self):
        if not self.is_markdown_document():
            return
        self.preview_container.setVisible(True)
        self.preview_is_visible = True
        self.editor_preview_splitter.setSizes([0, 1200])

    def show_split_view(self):
        if not self.is_markdown_document():
            return
        self.preview_container.setVisible(True)
        self.preview_is_visible = True
        self.editor_preview_splitter.setSizes([600, 600])

    # --------------------------------------------------------
    # ABOUT
    # --------------------------------------------------------

    def about(self):

        QMessageBox.about(
            self,
            "About MarkFlow",
            """
            <h2>MarkFlow 0.1</h2>
            <p>Native Markdown and PDF editor for Linux.</p>
            <p>Built with Python, PyQt6, Pandoc and XeLaTeX.</p>
            """
        )


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

def main():

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    icon_path = Path(__file__).resolve().parent / "markflow.png"
    app_icon = QIcon(str(icon_path))
    app.setWindowIcon(app_icon)

    window = MarkFlow()
    window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
