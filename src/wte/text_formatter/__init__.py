# -*- coding: utf-8 -*-
u"""
#########################
:mod:`wte.text_formatter`
#########################

This module contains functions for formatting the instruction texts shown to
the student.

.. moduleauthor:: Mark Hall <mark.hall@mail.room3b.eu>
"""
from docutils import core

from . import docutils_ext  # NOQA

SETTINGS = {}


def init(settings):
    """Initialise the module and all docutils extensions.
    """
    global SETTINGS
    docutils_ext.init(settings)
    SETTINGS['initial_header_level'] = 2
    SETTINGS['raw_enabled'] = False
    SETTINGS['file_insertion_enabled'] = False


def compile_rst(text):
    u"""Compiles the given ReStructuredText into HTML. Returns only the actual
    content of the generated HTML document, without headers or footers.

    :param text: The ReST to compile
    :type text: `unicode`
    :return: The body content of the generated HTML
    :return_type: `unicode`
    """
    parts = core.publish_parts(source=text, writer_name=u'html', settings_overrides=SETTINGS)
    return parts['body']
