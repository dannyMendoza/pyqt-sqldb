#!/usr/bin/env python

# This Python file uses the following encoding: utf-8

import datetime
from PySide6 import QtGui
from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex )
import time

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
                return QtGui.QColor('#1c1b1c')

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

if __name__ == "__main__":
    print('Local [TEST]')
