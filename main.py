#!/usr/bin/env python

# Daniel Mendoza

from qtcompleter.SQLTextEditor import ExecuteApp

if __name__ == '__main__':
    app = ExecuteApp(file=r'qtcompleter/test.sql')
    app.run()
