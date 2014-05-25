# -*- coding: utf-8 -*-
u"""
###############################################################
:mod:`wte.helpers.frontend` -- Helpers for the frontend display
###############################################################

The :mod:`~wte.helpers.frontend` module provides helper functionality used to
render the frontend page displays.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""

from genshi.builder import tag

def html_id(text):
    u"""Turns a given text into a valid HTML id attribute value. Removes
    spaces and full-stops.
    
    :param text: The text to convert
    :type text: `unicode`
    :return: The corresponding HTML id
    :rtype: `unicode`
    """
    return text.replace(' ', '_').replace('.', '_')

CODEMIRROR_MODES = {'text/html': ['javascript', 'css', 'xml', 'htmlmixed'],
                    'text/css': ['css'],
                    'text/javascript': ['javascript']}

def codemirror_scripts(request, mimetypes):
    u"""Generates the ``<script>`` tags necessary to load the CodeMirror mode
    JS files for the given list of ``mimetypes``.
    
    :param request: The request to use for generating URLs
    :type request: `~pyramid.request.Request`
    :param mimetypes: The mimetypes to load the CodeMirror modes for
    :type mimetypes: `list` of `unicode`
    :return: The necessary ``<script>`` tags
    """
    modes = []
    for mimetype in mimetypes:
        if mimetype in CODEMIRROR_MODES:
            modes.extend(CODEMIRROR_MODES[mimetype])
    return tag([tag.script(src=request.static_url('wte:static/js/codemirror/mode/%s/%s.js' % (mode, mode))) for mode in modes])