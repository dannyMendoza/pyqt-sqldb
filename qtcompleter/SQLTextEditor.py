#!/usr/bin/env python

# Daniel Mendoza

# References
# [QCompleter]
# https://doc.qt.io/qtforpython-6/overviews/qtwidgets-tools-customcompleter-example.html
# [QSyntaxHighlighter]
# https://doc.qt.io/qtforpython-6/examples/example_widgets_richtext_syntaxhighlighter.html

from PySide6.QtCore import (
        QEvent,
        QFile,
        QStringListModel,
        Qt,
        QTextStream,
        QRegularExpression,
        QRegularExpressionMatch,
        QSortFilterProxyModel,
        Signal,
        Slot)
from PySide6.QtGui import (
        QAction,
        QColor,
        QCursor,
        QFont,
        QFontMetricsF,
        QFontDatabase,
        QKeySequence,
        QTextCursor,
        QTextCharFormat,
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
        QPushButton,
        QTableView,
        QTextEdit,
        QVBoxLayout,
        QWidget)

from os import fspath
from pathlib import Path

import csv
import io
import re

if __name__ == '__main__':
    from db.DBQuery import Query
    import customcompleter_rc
    from TableView import CustomTableView
else:
    from . db.DBQuery import Query
    from . import customcompleter_rc
    from .TableView import CustomTableView

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
        pattern = r"\b[^'\\]([0-9]+\.[0-9]+|[0-9]+)\b[^'\\]"
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
        cr.setWidth(self._completer.popup().sizeHintForColumn(0) + self._completer.popup().verticalScrollBar().sizeHint().width())
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

        self.table_widget = QWidget()

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
        self.completingTextEdit.textChanged.connect(self.addColumnData)

        # Buttons
        self.btn_query = QPushButton('Execute')
        self.btn_close = QPushButton('Close')

        # Button Shortcuts
        self.btn_query.setShortcut(QKeySequence(QKeySequence(Qt.CTRL|Qt.Key_R)))

        # Buttons Functionality
        self.btn_close.clicked.connect(self.close)
        self.btn_query.clicked.connect(self.executeQuery)

        # Grid, Vertical & Horizontal layout(s)
        self.vlayout = QVBoxLayout()
        self.glayout = QGridLayout()
        self.glayout.addWidget(self.btn_query, 0, 0, 1, 2)
        self.glayout.addWidget(self.btn_close, 0, 2, 1, 1)
        self.vlayout.addWidget(self.completingTextEdit)
        self.glayout.addLayout(self.vlayout, 2, 0, 1, 3)
        widget = QWidget()
        widget.setLayout(self.glayout)
        self.setCentralWidget(widget)
        self.completingTextEdit.setFocus()
        self.resize(500, 300)
        self.setWindowTitle("DCS-DB Editor")

    def closeEvent(self, event):
        self.closed.emit()
        self.close_connection()
        super().closeEvent(event)
        self.close()

    @Slot()
    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Copy) and type(source) == QTableView:
                # Source -> Current TableView
                self.copySelection(source)
                return True
            elif event.matches(QKeySequence.Paste) and type(source) == TextEdit:
                self.textPasted()
        return super().eventFilter(source, event)

    def textPasted(self):
        text = self.completingTextEdit.toPlainText()
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


    def copySelection(self, source):
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
                QApplication.clipboard().setText(stream.getvalue())
                return
            QApplication.clipboard().setText(str(table[0][0]))
            return

    def addColumnData(self):
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

            # SQL Syntax Highlighter (Columns)
            # self.completingTextEdit.setup_editor(column=table_cols)

            dups = set(self.completer_list)
            dups.update(table_cols)
            self.completer_list = list(dups)
            self.completer_list.sort(key=len)

            self.completerModel.setStringList(self.completer_list)
            self.completingTextEdit.setCompleter(self.completer)
            sqlcursor.close()

    def fillTable(self, data: list=[]):
        for i in range(self.vlayout.count()):
            if i == 0:
                continue
            child = self.vlayout.itemAt(i).widget()
            #print(child)
            child.deleteLater()
        if isinstance(data, list):
            for record, cursor in data:
                table = QTableView()
                table.setAlternatingRowColors(True)
                table.installEventFilter(self)
                self.vlayout.addWidget(table)
                d = record, cursor
                model = CustomTableView(d)
                table.setModel(model)
                horizontal_header = table.horizontalHeader()
                vertical_header = table.verticalHeader()
                horizontal_header.setSectionResizeMode(
                        #QHeaderView.Interactive
                        QHeaderView.ResizeToContents
                        )
                vertical_header.setSectionResizeMode(
                        QHeaderView.Interactive
                        )
                horizontal_header.setStretchLastSection(False)
                cursor.close()
            return

    def executeQuery(self):
        text = self.completingTextEdit.toPlainText()
        if text:
            data = self.query_exe(text)
        else:
            # Return if TextEdit is empty
            return
        if isinstance(data, list):
            self.fillTable(data=data)
            return
        return

    def newFile(self):
        for i in range(self.vlayout.count()):
            if i == 0:
                continue
            child = self.vlayout.itemAt(i).widget()
            # print(child)
            child.deleteLater()
        self.completingTextEdit.clear()
        self.completingTextEdit.setFocus()

    def openFile(self, path=""):
        for i in range(self.vlayout.count()):
            if i == 0:
                continue
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

        text = self.completingTextEdit.toPlainText()
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

                    # SQL Syntax Highlighter (Columns)
                    # self.completingTextEdit.setup_editor(column=table_cols)

                    dups = set(self.completer_list)
                    dups.update(table_cols)
                    self.completer_list = list(dups)
                    self.completer_list.sort(key=len)

                    self.completerModel.setStringList(self.completer_list)
                    self.completingTextEdit.setCompleter(self.completer)
                    sqlcursor.close()

    def createMenu(self):
        file_menu = self.menuBar().addMenu(self.tr("&File"))

        new_file = file_menu.addAction(self.tr("&New..."))
        new_file.setShortcut(QKeySequence(QKeySequence.New))
        new_file.triggered.connect(self.newFile)


        open_file = file_menu.addAction(self.tr("&Open..."))
        open_file.setShortcut(QKeySequence(QKeySequence.Open))
        open_file.triggered.connect(self.openFile)
        return

        exitAction = QAction("Exit", self)
        aboutAct = QAction("About", self)
        aboutQtAct = QAction("About Qt", self)

        exitAction.triggered.connect(QApplication.instance().quit)
        aboutAct.triggered.connect(self.about)
        aboutQtAct.triggered.connect(QApplication.instance().aboutQt)

        fileMenu = self.menuBar().addMenu("File")
        fileMenu.addAction(exitAction)

        helpMenu = self.menuBar().addMenu("About")
        helpMenu.addAction(aboutAct)
        helpMenu.addAction(aboutQtAct)

    def modelFromFile(self, fileName):
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


class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        QSyntaxHighlighter.__init__(self, parent)
        self._mappings = {}

        quotes_color = QColor("#FF0000")
        quotes_format  = QTextCharFormat()
        quotes_format.setForeground(quotes_color)
        self.single = (QRegularExpression("\'"),None,1,quotes_format)
        #self.double = (QRegularExpression("\""),None,2,quotes_format)

        #startExpression = QRegularExpression("(/\\*|'|\")")
        multiLine_color = QColor("#4d491d")
        multiLineCommentFormat = QTextCharFormat()
        multiLineCommentFormat.setForeground(multiLine_color)
        startExpression = QRegularExpression("/\\*")
        endExpression = QRegularExpression(f"\\*/")
        self.comment = (startExpression, endExpression,3,multiLineCommentFormat)

    def add_mapping(self, pattern, format):
        self._mappings[pattern] = format

    def highlightBlock(self, text):
        pt = True
        for pattern, format in self._mappings.items():
            for match in re.finditer(pattern, text, re.MULTILINE):
                if '--' in match.string:
                    pt = False
                start, end = match.span()
                self.setFormat(start, end - start, format)

        self.setCurrentBlockState(0)

        if pt:
            quotes_multiline =  self.match_multiline(text, *self.single)

        comment_multiline = self.match_multiline(text, *self.comment)

    def match_multiline(self, text, delimiter, endDelimiter, in_state, style):
        if not endDelimiter:
            endDelimiter = delimiter

        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        else:
            match = delimiter.match(text)
            start = match.capturedStart()
            add = match.capturedLength()

        while start >= 0:
            match = endDelimiter.match(text, start + add)
            end =  match.capturedStart()
            if end >= add:
                length = end - start + match.capturedLength()
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add # - match.capturedLength()

            self.setFormat(start, length, style)
            match = delimiter.match(text, start + length)
            start = match.capturedStart()

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False


class ExecuteApp():
    def __init__(self, file: str=None):
        self.file = file
        pass

    def run(self):
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
    file = 'test.sql'
    app = ExecuteApp(file)
    app.run()
