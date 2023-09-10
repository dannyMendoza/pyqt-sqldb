#!/usr/bin/env python

# Daniel Mendoza

from editor.sqlcode_editor import ExecuteApp

if __name__ == '__main__':
    app = ExecuteApp(file=r'test.sql')
    app.run()
