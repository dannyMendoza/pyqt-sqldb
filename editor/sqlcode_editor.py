#!/usr/bin/env python

# Daniel Mendoza

# References

# [QCompleter]
# https://doc.qt.io/qtforpython-6/overviews/qtwidgets-tools-customcompleter-example.html
# [QSyntaxHighlighter]
# https://doc.qt.io/qtforpython-6/examples/example_widgets_richtext_syntaxhighlighter.html
# [QTextEdit->CodeEditor->ShowLineNumber]
# https://doc.qt.io/qtforpython-6.2/examples/example_widgets__codeeditor.html
# https://stackoverflow.com/questions/2443358/how-to-add-lines-numbers-to-qtextedit

from PySide6.QtCore import (
        QEvent,
        QFile,
        Qt,
        QTextStream,
        QRect,
        QRectF,
        QRegularExpression,
        QSize,
        QStringListModel,
        Signal,
        Slot)
from PySide6.QtGui import (
        QAction,
        QColor,
        QCursor,
        QFont,
        QFontMetricsF,
        QIcon,
        QKeySequence,
        QPainter,
        QPaintEvent,
        QResizeEvent,
        QTextCursor,
        QTextCharFormat,
        QTextFormat,
        QSyntaxHighlighter
        )
from PySide6.QtWidgets import (
        QApplication,
        QCompleter,
        QFileDialog,
        QGridLayout,
        QHeaderView,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QTableView,
        QTextEdit,
        QVBoxLayout,
        QScrollArea,
        QSplitter,
        QWidget
        )

from os import fspath
from pathlib import Path

import csv
import io
import re

if __name__ == '__main__':
    import customcompleter_rc
    import rc_icons
    from db.db_query import Query
    from highlighter import Highlighter
    from linenumber import LineNumberArea
    from table_view import CustomTableView
else:
    from .import customcompleter_rc
    from .import rc_icons
    from .db.db_query import Query
    from .highlighter import Highlighter
    from .linenumber import LineNumberArea
    from .table_view import CustomTableView

class TextEdit(QTextEdit):
    def __init__(self, parent=None, table: list=[]):
        super(TextEdit, self).__init__(parent)

        self.org = False
        self._completer = None
        isShortcut = None

        # SQL Syntax Highlighter
        self._highlighter = Highlighter()

        # Make tab -> 4 spaces
        self.setTabStopDistance(QFontMetricsF(self.font()).horizontalAdvance('  ')*5.4)

        self.table_completer = QCompleter(self)
        self.completerModel = QStringListModel()
        self.completerModel.setStringList(table)
        self.table_completer.setModel(self.completerModel)

        # Show Line Numbers
        self.lineNumberArea = LineNumberArea(self)
        self.document().blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.verticalScrollBar().valueChanged.connect(self.updateLineNumberArea)
        self.textChanged.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.updateLineNumberArea)
        self.highlight_current_line()

        # Highlight Current Line
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.updateLineNumberAreaWidth(0)

    def lineNumberAreaWidth(self):
        digits = 1
        m = max(1, self.document().blockCount())
        while m >= 10:
            m /= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, newBlockCount: int):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberAreaRect(self, rect_f: QRectF):
        self.updateLineNumberArea()

    def updateLineNumberAreaInt(self, slider_pos: int):
        self.updateLineNumberArea()

    def updateLineNumberArea(self):
        """
        When the signal is emitted, the sliderPosition has been adjusted
        according to the action, but the value has not yet been propagated
        (meaning the valueChanged() signal was not yet emitted), and the visual
        display has not been updated. In slots connected to self signal you can
        thus safely adjust any action by calling setSliderPosition() yourself,
        based on both the action and the slider's value.
        """

        # Make sure the sliderPosition triggers one last time the valueChanged() signal with the actual value !!!!
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition())

        # Since "QTextEdit" does not have an "updateRequest(...)" signal, we chose
        # to grab the imformation from "sliderPosition()" and "contentsRect()".
        # See the necessary connections used (Class constructor implementation part).

        rect = self.contentsRect()

        self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        self.updateLineNumberAreaWidth(0)

        dy = self.verticalScrollBar().sliderPosition()
        if dy > -1:
            self.lineNumberArea.scroll(0, dy)

        # Adjust slider to always see the number of the currently being edited line...
        first_block_id = self.getFirstVisibleBlockId()
        if first_block_id == 0 or self.textCursor().block().blockNumber() == first_block_id-1:
            self.verticalScrollBar().setSliderPosition(dy-self.document().documentMargin())

    def resizeEvent(self, event: QResizeEvent):
        QTextEdit.resizeEvent(self, event)

        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def getFirstVisibleBlockId(self) -> int:
        # Detect the first block for which bounding rect - once translated
        # in absolute coordinated - is contained by the editor's text area

        # Costly way of doing but since "blockBoundingGeometry(...)" doesn't
        # exists for "QTextEdit"...

        curs = QTextCursor(self.document())
        curs.movePosition(QTextCursor.Start)
        for i in range(self.document().blockCount()):
            block = curs.block()

            r1 = self.viewport().geometry()
            r2 = self.document().documentLayout().blockBoundingRect(block).translated(
                    self.viewport().geometry().x(), self.viewport().geometry().y() - (
                        self.verticalScrollBar().sliderPosition()
                        )).toRect()

            if r1.contains(r2, True):
                return i

            curs.movePosition(QTextCursor.NextBlock)
        return 0

    def lineNumberAreaPaintEvent(self, event: QPaintEvent):
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition())

        painter = QPainter(self.lineNumberArea)
        font = painter.font()
        painter.fillRect(event.rect(), QColor(200, 200, 200))
        blockNumber = self.getFirstVisibleBlockId()

        block = self.document().findBlockByNumber(blockNumber)

        if blockNumber > 0:
            prev_block = self.document().findBlockByNumber(blockNumber - 1)
        else:
            prev_block = block

        if blockNumber > 0:
            translate_y = -self.verticalScrollBar().sliderPosition()
        else:
            translate_y = 0

        top = self.viewport().geometry().top()

        # Adjust text position according to the previous "non entirely visible" block
        # if applicable. Also takes in consideration the document's margin offset.

        if blockNumber == 0:
            # Simply adjust to document's margin
            additional_margin = self.document().documentMargin() -1 - self.verticalScrollBar().sliderPosition()
        else:
            # Getting the height of the visible part of the previous "non entirely visible" block
            additional_margin = self.document().documentLayout().blockBoundingRect(prev_block) \
                    .translated(0, translate_y).intersected(self.viewport().geometry()).height()

        # Shift the starting point
        top += additional_margin

        bottom = top + int(self.document().documentLayout().blockBoundingRect(block).height())

        col_1 = QColor(0, 0, 0)      # Current line (Black)
        col_0 = QColor(120, 120, 120)    # Other lines  (custom darkgrey)

        # Draw the numbers (displaying the current line number in Black)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = f"{blockNumber + 1}"
                painter.setPen(QColor(120, 120, 120))

                font.setBold(False)

                if self.textCursor().blockNumber() == blockNumber:
                    painter.setPen(col_1)
                    font.setBold(True)
                else:
                    painter.setPen(col_0)

                painter.setFont(font)

                painter.drawText(-5, top,
                                 self.lineNumberArea.width(), self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.document().documentLayout().blockBoundingRect(block).height())
            blockNumber += 1

    @Slot()
    def highlight_current_line(self):
        """
        A format that is used to specify a foreground or background brush/color
        for the selection.

        ExtraSelection provides a way of specifying a character format for a
        given selection in a document
        """
        extra_selections = []

        if not self.isReadOnly():
            selection = self.ExtraSelection()

            line_color = QColor(200, 200, 200).lighter(110)
            selection.format.setBackground(line_color)

            selection.format.setProperty(QTextFormat.FullWidthSelection, True)

            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()

            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def setup_editor(self, kw: list=[], table: list=[], column: list=[]):
        """
        kw: list
        table: list
        column: list (OPTIONAL)

        kw -> Highlight SQL KeyWords
        table -> Highlight Table Names
        column -> Highlight Column Names
        """

        # Font (Foreground) Colors
        digit_color = QColor("#FF0000")
        comment_color = QColor("#4d491d")
        sql_color = QColor("#0e1791")
        table_color = QColor("#99005e")

        sql_format = QTextCharFormat()
        sql_format.setForeground(sql_color)
        # sql_format.setFontCapitalization(QFont.AllUppercase)
        for word in kw:
            pattern = fr'(\b{word}\b)'
            self._highlighter.add_mapping(pattern, sql_format)

        table_format = QTextCharFormat()
        table_format.setForeground(table_color)
        #table_format.setFontWeight(QFont.Bold)
        for word in table:
            pattern = fr'(\b{word}\b)'
            self._highlighter.add_mapping(pattern, table_format)

        digit_format = QTextCharFormat()
        digit_format.setForeground(digit_color)
        #pattern = r"\b[^'\\]([0-9]+|[0-9]+\.[0-9]+)\b[^'\\]"
        pattern = r"^\b(?=.)([+-]?([0-9]*)(\.([0-9]+))?)\b"
        self._highlighter.add_mapping(pattern, digit_format)

        comment_format = QTextCharFormat()
        comment_format.setForeground(comment_color)
        pattern = r'--.*$'
        self._highlighter.add_mapping(pattern, comment_format)

#        pattern = r'/\*(.*)\*/'
#        self._highlighter.add_mapping(pattern, comment_format)

        #pattern = r'/\*.*\*/'
        #pattern = r'^(.+)(?:\n|\r\n?)((?:(?:\n|\r\n?).+)+)'
        #print(self._highlighter.get_mapping())
        # Column is commented out as it does not work correctly when pasting text
        # column_format = QTextCharFormat()
        # column_format.setForeground(QColor("#d8baf7"))
        # column_format.setFontItalic(True)
        # for word in column:
        #     pattern = fr'(\b{word}\b)'
        #     self._highlighter.add_mapping(pattern, column_format)

        self._highlighter.setDocument(self.document())

    def insertFromMimeData(self, source):
        """
        source: None

        The source can be text, image, url, etc.
        If the source is text then it is inserted (pasted) as Plain Text
        """
        if source.hasText():
            self.insertPlainText(source.text())
        elif source.hasImage():
            cursor = self.textCursor()
            image = source.imageData()
            cursor.insertImage(image)
        else:
            return
        return

    def setCompleter(self, c):
        if self._completer is not None:
            self._completer.activated.disconnect()

        self._completer = c

        c.setWidget(self)
        c.setCompletionMode(QCompleter.PopupCompletion)
        c.activated.connect(self.insertCompletion)

    def completer(self):
        return self._completer

    def insertCompletion(self, completion):
        if self._completer.widget() is not self:
            return

        extra = len(completion) - len(self._completer.completionPrefix())

        tc = self.textCursor()
        if not self.char_check:
            tc.select(QTextCursor.WordUnderCursor)
            tc.insertText(completion)
            return

        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)

        return tc.selectedText()

    def focusInEvent(self, e):
        if self._completer is not None:
            self._completer.setWidget(self)

        super(TextEdit, self).focusInEvent(e)

    def tableCompleter(self):
        self.org = self._completer
        self.setCompleter(self.table_completer)
        self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0, 0))
        cr = self.cursorRect()
        cr.setWidth(self._completer.popup().sizeHintForColumn(0) +
                    self._completer.popup().verticalScrollBar().sizeHint().width())
        self._completer.complete(cr)

    def keyPressEvent(self, e):
        if self._completer is not None and self._completer.popup().isVisible():
            # The following keys are forwarded by the completer to the widget.
            if e.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
                e.ignore()
                # Let the completer do default behavior.
                return
        #if e.key() == Qt.Key_Tab:
        #    tc = self.textCursor()
        #    tc.insertText("    ")
        #    return


        isShortcut = (e.modifiers() & Qt.ControlModifier) and e.key() == Qt.Key_M
        if self._completer is None or not isShortcut:
            # Do not process the shortcut when we have a completer.
            super(TextEdit, self).keyPressEvent(e)

        ctrlOrShift = e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
        if self._completer is None or (ctrlOrShift and len(e.text()) == 0):
            return

        eow = "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-="
        hasModifier = (e.modifiers() != Qt.NoModifier) and not ctrlOrShift
        completionPrefix = self.textUnderCursor()

        self._completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)

        # If current text is lower/upper or mixed set CaseSensitive or
        # CaseInsensitive accordingly
        self.char_check = 1 if self.textUnderCursor().isupper() \
                else 2 if self.textUnderCursor().islower() else False
        cc = self.char_check
        if cc:
            self._completer.setCaseSensitivity(Qt.CaseSensitive)
        else:
            self._completer.setCaseSensitivity(Qt.CaseInsensitive)

        if not isShortcut and (hasModifier or len(e.text()) == 0 or len(completionPrefix) < 1 or e.text()[-1] in eow):
            self._completer.popup().hide()
            return

        if isShortcut:
            self.tableCompleter()
            return
        else:
            if self.org and not self._completer.popup().isVisible():
                # Set default completer
                self.setCompleter(self.org)
                self.org = False
                return

        if completionPrefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(completionPrefix)
            index = self._completer.completionModel().index(0, 0)
            self._completer.popup().setCurrentIndex(index)
            current_index = self._completer.popup().currentIndex()
            item = current_index.data(Qt.DisplayRole)
            if item == completionPrefix:
                self._completer.setCompletionPrefix(item)
                self._completer.popup().hide()
                return

            self._completer.popup().setCurrentIndex(
                    self._completer.completionModel().index(0, 0))

            cr = self.cursorRect()
            cr.setWidth(self._completer.popup().sizeHintForColumn(0) +
                        self._completer.popup().verticalScrollBar().sizeHint().width())
            self._completer.complete(cr)


class MainWindow(QMainWindow, Query):
    closed = Signal()
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.create_actions()
        self.createMenu()

        sqlcursor = self.con.cursor()
        query = (
                'SELECT name '
                'FROM sqlite_schema '
                'WHERE type="table" AND '
                'name NOT LIKE "sqlite_%" '
                'ORDER BY name;'
                )
        out = sqlcursor.execute(query)
        self.table_list = [table[0] for table in out]
        self.table_list.extend([table.upper() for table in self.table_list])
        self.all_tables = []
        sqlcursor.close()

        # SQL Current DB Table Syntax Highlighter
        self.table_list.sort()

        # Init TextEdit passing the List of Tables (Variable: table)
        # If Ctrl-P (Shortcut) then it will popup autocompletion
        # for the current DB tables
        self.completingTextEdit = TextEdit(table=self.table_list)
        self.completingTextEdit.installEventFilter(self)

        self.completer = QCompleter(self)
        self.completerModel = self.modelFromFile(':/resources/wordlist.txt')
        self.completer_list = self.completerModel.stringList()

        # SQL KeyWord Syntax Highlighter
        self.list_copy = self.completer_list.copy()
        self.list_copy.sort()

        self.completer_list.extend(self.table_list)
        self.completer_list.sort(key=len)
        self.completerModel.setStringList(self.completer_list)
        # print(completerModel.stringList())
        self.completer.setModel(self.completerModel)
        self.completer.setWrapAround(False)

        self.completingTextEdit.setup_editor(kw=self.list_copy, table=self.table_list)

        self.completingTextEdit.setCompleter(self.completer)

        # Signals
        self.completingTextEdit.textChanged.connect(self.addColumnData)
        self.completingTextEdit.cursorPositionChanged.connect(self.textPasted)
        self.last_position = None

        # Buttons
        self.btn_query = QPushButton('Execute')
        self.btn_close = QPushButton('Close')
        self.btn_hide = QPushButton('Hide Table Data')

        # Button Shortcuts
        self.btn_query.setShortcut(QKeySequence(QKeySequence(Qt.CTRL|Qt.Key_R)))

        # Buttons Functionality
        self.btn_close.clicked.connect(self.close)
        self.btn_query.clicked.connect(self.executeQuery)
        self.btn_hide.clicked.connect(self.toggle_table_visibility)

        # Scroll Area
        scroll_area = QWidget()

        # Vertical layout
        self.vlayout = QVBoxLayout(scroll_area)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVisible(False)
        self.scroll.setWidget(scroll_area)

        # Grid layout
        self.glayout = QGridLayout()
        self.glayout.addWidget(self.btn_query, 0, 0, 1, 2)
        self.glayout.addWidget(self.btn_close, 0, 2, 1, 1)
        self.glayout.addWidget(self.completingTextEdit, 1, 0, 1, 3)
        self.glayout.addWidget(self.scroll, 2, 0, 1, 3)
        # self.glayout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(self.glayout)
        self.setCentralWidget(widget)

        self.completingTextEdit.setFocus()
        self.resize(500, 300)
        self.setWindowTitle("DMNIX* DB Editor")

    def closeEvent(self, event: QEvent):
        self.closed.emit()
        self.close_connection()
        super().closeEvent(event)
        #self.close()

    @Slot()
    def eventFilter(self, source, event) -> super:
        if event and event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Copy) and type(source) == QTableView:
                # Source -> Current TableView
                self.copySelection(source)
                return True
            elif event.matches(QKeySequence.Paste) and type(source) == TextEdit:
                self.get_cursor()
        return super().eventFilter(source, event)

    def get_cursor(self) -> int:
        cursor = self.completingTextEdit.textCursor()
        self.last_position = cursor.position()
        return self.last_position

    def textPasted(self, whole: bool=False) -> None:
        """Add table column data to QCompleter

        Keyword arguments:
        whole -- read all text (default False)
        """
        if whole:
            text = self.completingTextEdit.toPlainText()
        else:
            if not self.last_position:
                # Paste event not triggered
                return
            position = self.completingTextEdit.textCursor().position()
            last_position = self.last_position
            self.last_position = None
            # print(f'{last_position=} {position=}')
            text = self.completingTextEdit.toPlainText()[last_position:position]

        tables = {table for table in self.table_list if table in text}
        if tables:
            for table in tables:
                if table not in self.all_tables:
                    self.all_tables.append(table)
                    sqlcursor = self.con.cursor()
                    print(f'{self.all_tables[-1]}')
                    query = (
                            'SELECT name '
                            f'FROM pragma_table_info("{table}") '
                            'ORDER BY name;'
                            )
                    out = sqlcursor.execute(query)
                    table_cols = [column[0] for column in out]
                    print(f'{table_cols}\n')
                    table_cols.extend([column.upper() for column in table_cols])
                    table_cols.sort()

                    # SQL Syntax Highlighter (Columns)
                    # self.completingTextEdit.setup_editor(column=table_cols)

                    dups = set(self.completer_list)
                    dups.update(table_cols)
                    self.completer_list = list(dups)
                    self.completer_list.sort(key=len)

                    self.completerModel.setStringList(self.completer_list)
                    self.completingTextEdit.setCompleter(self.completer)
                    sqlcursor.close()
        return

    def copySelection(self, source: QTableView)  -> str:
        selection = source.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            # hcolumns -> no dups for multiple rows under same column
            hcolumns = list(set(columns))
            row_count = rows[-1] - rows[0] + 1
            col_count = columns[-1] - columns[0] + 1
            hor_headers = source.model().headers
            # get selected headers
            sel_headers = [hor_headers[h] for h in hcolumns]
            table = [[''] * col_count for _ in range(row_count)]
            for index in selection:
                row = index.row() - rows[0]
                column = index.column() - columns[0]
                table[row][column] = index.data()
            stream = io.StringIO()
            if len(table) > 1 or len(table[0]) > 1:
                table.insert(0, sel_headers)
                csv.writer(stream, delimiter='\t').writerows(table)
                return QApplication.clipboard().setText(stream.getvalue())
            return QApplication.clipboard().setText(str(table[0][0]))

    def addColumnData(self) -> None:
        cursor = self.completingTextEdit.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        selected_text = cursor.selectedText().strip()
        if selected_text in self.table_list and selected_text not in self.all_tables:
            self.all_tables.append(selected_text)
            sqlcursor = self.con.cursor()
            print(f'{self.all_tables[-1]}')
            query = (
                    'SELECT name '
                    f'FROM pragma_table_info("{selected_text}") '
                    'ORDER BY name;'
                    )
            out = sqlcursor.execute(query)
            table_cols = [column[0] for column in out]
            print(f'{table_cols}\n')
            table_cols.extend([column.upper() for column in table_cols])
            table_cols.sort()

            # SQL Syntax Highlighter (Columns)
            # self.completingTextEdit.setup_editor(column=table_cols)

            dups = set(self.completer_list)
            dups.update(table_cols)
            self.completer_list = list(dups)
            self.completer_list.sort(key=len)

            self.completerModel.setStringList(self.completer_list)
            self.completingTextEdit.setCompleter(self.completer)
            sqlcursor.close()

    def toggle_table_visibility(self) -> None:
        f = False
        for i in range(self.vlayout.count()):
            if i == 0:
                continue
            child = self.vlayout.itemAt(i).widget()
            if child.isVisible():
                self.btn_hide.setText('Show Table Data')
                child.setVisible(False)
                f = True
            else:
                self.btn_hide.setText('Hide Table Data')
                child.setVisible(True)
        if f:
            self.glayout.setRowStretch(0,1)
            self.glayout.setRowStretch(1,30)
            self.glayout.setRowStretch(2,1)
            return
        self.glayout.setRowStretch(0,1)
        self.glayout.setRowStretch(1,50)
        self.glayout.setRowStretch(2,50)

    def fillTable(self, data: list=[]) -> None:
        for i in range(self.vlayout.count()):
            if i == 0:
                continue
            child = self.vlayout.itemAt(i).widget()
            if isinstance(child, QTableView):
            # print(child)
                child.deleteLater()
        if isinstance(data, list):
            self.scroll.setVisible(True)
            self.btn_hide.setText('Hide Table Data')
            self.vlayout.addWidget(self.btn_hide)
            self.glayout.setRowStretch(0,1)
            self.glayout.setRowStretch(1,30)
            self.glayout.setRowStretch(2,60)
            for record, cursor in data:
                table = QTableView()
                table.setAlternatingRowColors(True)
                table.installEventFilter(self)
                table.setMinimumSize(QSize(100,300))
                self.vlayout.addWidget(table)
                d = record, cursor
                model = CustomTableView(d)
                table.setModel(model)
                horizontal_header = table.horizontalHeader()
                vertical_header = table.verticalHeader()
                if horizontal_header:
                    horizontal_header.setSectionResizeMode(
                            #QHeaderView.Interactive
                            QHeaderView.ResizeToContents
                            )
                    horizontal_header.setStretchLastSection(False)
                if vertical_header:
                    vertical_header.setSectionResizeMode(
                            QHeaderView.Interactive
                            )
                cursor.close()
            return

    def executeQuery(self) -> None:
        text = self.completingTextEdit.toPlainText()
        if text:
            data = self.query_exe(text)
        else:
            # Return if TextEdit is empty
            return
        if data and isinstance(data, list):
            self.fillTable(data=data)
            return
        print(f'Empty: {data=}')
        return

    def newFile(self) -> None:
        for i in range(self.vlayout.count()):
            child = self.vlayout.itemAt(i).widget()
            # print(child)
            child.deleteLater()
        self.scroll.setVisible(False)
        self.glayout.setRowStretch(0,1)
        self.glayout.setRowStretch(1,50)
        self.glayout.setRowStretch(2,0)
        self.completingTextEdit.clear()
        self.completingTextEdit.setFocus()

    def openFile(self, path: str="") -> None:
        for i in range(self.vlayout.count()):
            child = self.vlayout.itemAt(i).widget()
            # print(child)
            child.deleteLater()
        file_name = path
        if not file_name:
            file_name, _ = QFileDialog.getOpenFileName(
                    self, self.tr("Open File"), "", "SQL Files (*.sql)")

        if file_name:
            in_file = QFile(file_name)
            if in_file.open(QFile.ReadOnly | QFile.Text):
                stream = QTextStream(in_file)
                self.completingTextEdit.setPlainText(stream.readAll())

        self.scroll.setVisible(False)
        self.glayout.setRowStretch(0,1)
        self.glayout.setRowStretch(1,50)
        self.glayout.setRowStretch(2,0)
        self.textPasted(whole=True)

    def create_actions(self) -> None:
        icon = QIcon.fromTheme('document-new', QIcon(':/images/new.png'))
        self._new_query = QAction(
                icon,
                "&New Query",
                self, shortcut=QKeySequence.New,
                statusTip="Create New Query",
                triggered=self.newFile
                )

        icon = QIcon.fromTheme('document-open', QIcon(':/images/document-open.svg'))
        self._open_file = QAction(
                icon,
                "&Open File",
                self, shortcut=QKeySequence.Open,
                statusTip="Open File",
                triggered=self.openFile
                )

        icon = QIcon.fromTheme('application-exit', QIcon(':/images/application-exit.svg'))
        self._quit_app = QAction(
                icon,
                "&Quit",
                self, shortcut="Ctrl+Q",
                statusTip="Quit this sh**t application",
                triggered=self.close
                )

    def createMenu(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&File"))
        file_menu.addAction(self._new_query)
        file_menu.addAction(self._open_file)
        file_menu.addSeparator()
        file_menu.addAction(self._quit_app)

    def modelFromFile(self, fileName: str) -> QStringListModel:
        f = QFile(fileName)
        if not f.open(QFile.ReadOnly):
            return QStringListModel(self.completer)

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        words = []
        while not f.atEnd():
            line = f.readLine().trimmed()
            if line.length() != 0:
                try:
                    line = str(line, encoding='ascii')
                except TypeError:
                    line = str(line)

                words.append(line)

        QApplication.restoreOverrideCursor()

        return QStringListModel(words, self.completer)

    def about(self):
        QMessageBox.about(self, "About",
                "This example demonstrates the different features of the "
                "QCompleter class.")


class ExecuteApp():
    def __init__(self, file: str=None):
        self.file = file
        pass

    def run(self) -> None:
        import sys

        app = QApplication(sys.argv)
        window = MainWindow()
        window.resize(1200,600)
        window.show()
        if self.file:
            print(fspath(Path(self.file).resolve()))
            window.openFile(fspath(Path(self.file).resolve()))

        with open('style.qss', 'r') as qss:
            _style = qss.read()
            app.setStyleSheet(_style)

        sys.exit(app.exec())

if __name__ == '__main__':
    file = '../test.sql'
    app = ExecuteApp(file)
    app.run()
