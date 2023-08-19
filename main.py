#!/usr/bin/env python

# This Python file uses the following encoding: utf-8

import datetime
import pathlib
import sys
import sqlite3
from PySide6 import QtGui
from PySide6.QtCore import (
    QFile,
    Slot,
    Qt,
    Signal,
    QAbstractTableModel,
    QModelIndex,
    QEvent)
from PySide6.QtWidgets import (
    QCompleter,
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QBoxLayout,
    QVBoxLayout,
    QHBoxLayout,
    QHeaderView,
    QGridLayout,
    QTableWidget,
    QTextEdit,
    QDialogButtonBox,
    QTableView,
    QTableWidgetItem,
    QWidget)
import time
from threading import Thread
#st = time.time()
#time.sleep(0.012581348419189453)
#print('Hola')
#et = time.time()
#elapsed_time = et - st
#print(f'{elapsed_time=}')
#exit()

script_path = pathlib.Path(__file__).parent.absolute()

class DBConnection:
    def __init__(self):
        self.db = f'{script_path}/History'
        self.con = sqlite3.connect(self.db)
        self.cursor = self.con.cursor()

    def query_execution(self, query=None):
        if query is None:
            query = (
                    'SELECT * '
                    'FROM urls '
                    'WHERE url '
                    'LIKE "%music.youtube%" '
                    'ORDER BY last_visit_time desc '
                    'LIMIT 10;'
                    'SELECT * '
                    'FROM urls '
                    'WHERE url '
                    'LIKE "%spotify%" '
                    'ORDER BY last_visit_time desc '
                    'LIMIT 10;'
                    'SELECT * '
                    'FROM clusters '
                    'LIMIT 10;'
                    )
        query = list(filter(None, query.split(';')))
        # print(query)
        query_list = []
        if len(query) > 1:
            for i,q in enumerate(query,1):
                self.cursor = self.con.cursor()
                # i = Thread(target=self.cursor.execute(q), daemon=True, name='QUERY')
                i = self.cursor.execute(q)
                headers = [column[0] for column in i.description]
                t = headers, i
                query_list.append(t)
            #print(f'{query_list=}')
            return query_list
        else:
            query = ''.join(query).split('\n')
            o = None
            if query:
                o = query[0]
            if len(query) > 1 and o:
                for q in query[1:]:
                    if q.startswith('select'):
                        o += f'; {q}'
                        continue
                    o += f' {q}'
                query = o.split(';')
            if len(query) > 1:
                for i,q in enumerate(query,1):
                    self.cursor = self.con.cursor()
                    # print(Thread(target=self.cursor.execute(q), daemon=True, name='QUERY'))
                    i = self.cursor.execute(q)
                    headers = [column[0] for column in i.description]
                    t = headers, i
                    query_list.append(t)
                return query_list
            query = ''.join(query)
            self.cursor = self.con.cursor()
            out = self.cursor.execute(query)
            if out:
                headers = [column[0] for column in out.description]
                return headers, out
            return False

    def close_connection(self):
        self.cursor.close()
        self.con.close()
        print(f'{self.db} connection closed')

class CustomTableView(QAbstractTableModel):

    ROW_BATCH_COUNT = 15

    def __init__(self, data=None):
        super().__init__()
        # Load 15 row while user scroll down to a large set of records
        self.rowsLoaded = CustomTableView.ROW_BATCH_COUNT
        self.load_data(data)

    def load_data(self, data):
        self.beginResetModel()
        st = time.time()
        self.headers = data[0]
        self.records = [r for r in data[1]]
        et = time.time()
        elapsed_time = et - st
        print(f'{elapsed_time=}')
        self.column_count = len(self.headers)
        self.row_count = len(self.records)
        print(f'\nROWS: {self.row_count}')
        print(f'COLUMNS: {self.column_count}\n')
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        # Return rowsLoaded if the records is greater than ROW_BATCH_COUNT
        if self.row_count <= self.rowsLoaded:
            return self.row_count
        return self.rowsLoaded
        #return self.row_count

    def canFetchMore(self,index=QModelIndex()):
        # return True if the records is greater than ROW_BATCH_COUNT
        if self.row_count > self.rowsLoaded:
            return True
        return False

    def fetchMore(self,index=QModelIndex()):
        reminder = self.row_count - self.rowsLoaded # query records - ROW_BATCH_COUNT
        itemsToFetch = min(reminder,CustomTableView.ROW_BATCH_COUNT)
        self.beginInsertRows(QModelIndex(),self.rowsLoaded,self.rowsLoaded+itemsToFetch-1)
        self.rowsLoaded += itemsToFetch
        self.endInsertRows()

    def columnCount(self, parent=QModelIndex):
        return self.column_count

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.headers[section]
            return f'{section+1}'

    def data(self, index, role):
        column = index.column()
        row = index.row()
        self.value = self.records[row][column]

        # Text Color 'Foreground'
        if role == Qt.ForegroundRole:
            if isinstance(self.value, int) or isinstance(self.value, float):
                if self.value <= 0:
                    return QtGui.QColor('red')
            elif isinstance(self.value, datetime.datetime):
                return QtGui.QColor('blue')
            else:
                return QtGui.QColor('lightgreen')

        # Field 'Background'
        if role == Qt.BackgroundRole:
            if self.value == None or self.value == '':
                return QtGui.QColor('darkgray')

        # Row Alignment
        if role == Qt.TextAlignmentRole:
            if isinstance(self.value, int):
                return Qt.AlignVCenter + Qt.AlignRight

        if role == Qt.DisplayRole:
            if isinstance(self.value, datetime.datetime):
                self.value = str(self.value)
            return self.value


class DBWindow(QWidget):
    closed = Signal()
    def __init__(self):
        super().__init__()
        self.btn_query = QPushButton('Execute Query')
        self.btn_close = QPushButton('Close DB Connection')
        self.sqlTextEditor = QTextEdit()
        self.vlayout = QVBoxLayout()
        self.layout = QGridLayout()
        self.layout.addWidget(self.btn_query, 0, 0)
        self.layout.addWidget(self.btn_close, 0, 1)
        self.vlayout.addWidget(self.sqlTextEditor)
        self.layout.addLayout(self.vlayout, 2, 0, 1, 2)
        self.setLayout(self.layout)
        self.widget_list = []
        self.query_data = []
        self.sqlTextEditor.setFocus()


    @Slot()
    def closeEvent(self, event):
        self.closed.emit()
        self.close()

    @Slot()
    def fillTable(self, h=None, r=None, data=None):
        for i in range(self.vlayout.count()):
            if i == 0:
                continue
            child = self.vlayout.itemAt(i).widget()
            #print(child)
            child.deleteLater()
        if isinstance(data, list):
            for record, cursor in data:
                table = QTableView()
                self.vlayout.addWidget(table)
                d = record, cursor
                model = CustomTableView(d)
                table.setModel(model)
                horizontal_header = table.horizontalHeader()
                vertical_header = table.verticalHeader()
                horizontal_header.setSectionResizeMode(
                        QHeaderView.Interactive
                        #QHeaderView.ResizeToContents
                        )
                vertical_header.setSectionResizeMode(
                        QHeaderView.Interactive
                        )
                horizontal_header.setStretchLastSection(True)
                cursor.close()
            return
        table = QTableView()
        self.vlayout.addWidget(table)
        data = h, r
        model = CustomTableView(data)
        table.setModel(model)
        horizontal_header = table.horizontalHeader()
        vertical_header = table.verticalHeader()
        horizontal_header.setSectionResizeMode(
                QHeaderView.ResizeToContents
                )
        vertical_header.setSectionResizeMode(
                QHeaderView.Interactive
                )
        horizontal_header.setStretchLastSection(False)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('DM')
        self.button = QPushButton('Connect to DB')
        self.close_button = QPushButton('Close')
        self.label = QLabel('Not Connected')
        self.button.clicked.connect(self.button_cliked)
        self.close_button.clicked.connect(lambda: self.close())
        self.vlayout = QVBoxLayout(self)
        self.vlayout.addWidget(self.label)
        self.vlayout.addWidget(self.button)
        self.vlayout.addWidget(self.close_button)


    @Slot()
    def button_cliked(self):
        if self.label.text() in ('Not Connected','Last Connection History'):
            self.dbwindow = DBWindow()
            self.dbwindow.showMaximized()
            self.dbwindow.setWindowTitle('DATABASE')
            self.hide()
            self.dbconn = DBConnection()
            self.label.setText('Last Connection History')
            self.dbwindow.closed.connect(self.close_DBWindow)
            self.dbwindow.btn_close.clicked.connect(lambda: self.dbwindow.close())
            self.dbwindow.btn_query.clicked.connect(
                    lambda: self.query_execution())
        else:
            self.label.setText('Not Connected')

    @Slot()
    def close_DBWindow(self):
        self.dbwindow.close()
        self.dbconn.close_connection()
        self.showNormal()

    def query_execution(self):
        text = self.dbwindow.sqlTextEditor.toPlainText()
        #print(text)
        if text:
            data = self.dbconn.query_execution(text)
        else:
            data = self.dbconn.query_execution()
        if isinstance(data, list):
            t = Thread(target=self.dbwindow.fillTable(data=data))
            t.start()
            t.join()
            return

        h, r = data
        self.dbwindow.fillTable(h,r)

if __name__ == "__main__":
    # dbconn = DBConnection()
    # print(dbconn.query_execution())
    # exit()
    app = QApplication(sys.argv)
    # ...
    window = MainWindow()
    window.resize(200,100)
    window.show()

    with open('style.qss', 'r') as qss:
        _style = qss.read()
        app.setStyleSheet(_style)

    sys.exit(app.exec())
