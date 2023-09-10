#!/usr/bin/env python

from PySide6.QtCore import (
        QRegularExpression
        )
from PySide6.QtGui import (
        QColor,
        QTextCharFormat,
        QSyntaxHighlighter
        )

import re

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

