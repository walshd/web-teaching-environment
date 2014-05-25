# -*- coding: utf-8 -*-
u"""

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""

from genshi.builder import tag

def html_id(text):
    return text.replace(' ', '_').replace('.', '_')

CODEMIRROR_MODES = {'text/html': ['javascript', 'css', 'xml', 'htmlmixed']}

def codemirror_scripts(request, mimetypes):
    modes = []
    for mimetype in mimetypes:
        if mimetype in CODEMIRROR_MODES:
            modes.extend(CODEMIRROR_MODES[mimetype])
    return tag([tag.script(src=request.static_url('wte:static/js/codemirror/mode/%s/%s.js' % (mode, mode))) for mode in modes])