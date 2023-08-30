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
        # print(query)
        query_list = []
        o = False
        if query:
            o = query[0]
            if o.strip().startswith('--'):
                print(f'Comment: {o.strip()}')
                o = ''
            for q in query[1:]:
                if q.strip().startswith('select'):
                    o += f';{q}'
                    continue
                if q.strip().startswith('--'):
                    print(f'Comment: {q.strip()}')
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
