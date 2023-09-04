#!/usr/bin/env python

# This Python file uses the following encoding: utf-8

import datetime
import pathlib
import re
import sys
import sqlite3

from .DBConnection import DBConnection

script_path = pathlib.Path(__file__).parent.absolute()

class Query(DBConnection):
    def __init__(self):
        super().__init__()

    def query_exe(self, query=None):

        # Debug Query
        if query is None:
            query = (
                    'SELECT * '
                    'FROM urls '
                    'WHERE url '
                    'LIKE "%music.youtube%" '
                    'ORDER BY last_visit_time desc '
                    'LIMIT 1;'
                    'SELECT * '
                    'FROM urls '
                    'WHERE url '
                    'LIKE "%spotify%" '
                    'ORDER BY last_visit_time desc '
                    'LIMIT 1;'
                    )

        query = query.translate(str.maketrans({'\n':'~','\t':' '}))
        query = [q.strip() for q in re.split(r'~|;', query) if q.strip() != '']
        # query = list(filter(None, re.split(r'-|;', query.strip())))
        query_list = []
        multiline = False
        o = False
        if query:
            o = query[0].strip()
            if '--' in o:
                # Single Line Comment
                index = re.search(r'--',o).end()
                o = query[0][:index-2]
            elif '/*' in o:
                # Multi Line Comment
                index = re.search(r'/\*',o).start()
                # print(f'First o {o=}')
                if '*/' in o:
                    x = query[0][:index]
                    index = re.search(r'\*/',o).end()
                    x += query[0][index:]
                    # print(f'Second o {o=}')
                    multiline = False
                    o = x
                else:
                    o = query[0][:index]
                    multiline = True
            for q in query[1:]:
                if multiline:
                    index = re.search(r'\*/',q)
                    if index:
                        index = index.end()
                        #print(f'{q[index:]=}')
                        o += q[index:]
                        multiline = False
                    else:
                        continue
                elif '--' in q:
                    # Single Line Comment
                    index = re.search(r'--',q).end()
                    q = q[:index-2].lower().strip()
                    if q.startswith('select'):
                        o += f';{q}'
                    else:
                        o += q[:index-2].strip()
                    #print(f'SINGLE {o=}')
                elif '/*' in q:
                    # Multi Line Comment
                    index = re.search(r'/\*',q).start()
                    if '*/' in q:
                        x = q[:index]
                        index = re.search(r'\*/',q).end()
                        x += q[index:]
                        multiline = False
                        o += x
                    else:
                        o += q[:index-2]
                        multiline = True
                else:
                    if q.lower().strip().startswith('select'):
                        o += f';{q}'
                        continue
                    o += f' {q}'
            query = [q for q in o.split(';') if q != '']
            # print(query)
            if query:
                print('[Query]',*query, sep='\n', end='\n\n')
            for i,q in enumerate(query,1):
                self.cursor = self.con.cursor()
                # print(Thread(target=self.cursor.execute(q), daemon=True, name='QUERY'))
                try:
                    i = self.cursor.execute(q)
                    headers = [column[0] for column in i.description]
                    t = headers, i
                except sqlite3.OperationalError as e:
                    print(f'{str(e).title()}')
                    return
                query_list.append(t)
            return query_list
        return False
        #query = ''.join(query)
        #if query.strip().startswith('--'):
        #    return
        #print(f'\n[Single Query]\n{query[-1]}\n')
        #self.cursor = self.con.cursor()
        #try:
        #    out = self.cursor.execute(query[-1])
        #except sqlite3.OperationalError as e:
        #    print(f'{str(e).title()}')
        #    return
        #if out:
        #    headers = [column[0] for column in out.description]
        #    return headers, out
        #return False

if __name__ == "__main__":
    query = Query()
    query.query_exe()
    query.close_connection()
