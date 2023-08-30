#!/usr/bin/env python

# This Python file uses the following encoding: utf-8

import datetime
import pathlib
import sys
import sqlite3

script_path = pathlib.Path(__file__).parent.absolute()

class DBConnection:
    def __init__(self):
        self.db = f'{script_path}/History'
        self.con = sqlite3.connect(self.db)
        self.cursor = self.con.cursor()

    def close_connection(self):
        self.cursor.close()
        self.con.close()
        print(f'{self.db} connection closed')

if __name__ == "__main__":
    print('LOCAL (TEST)')
    dbconn = DBConnection()
