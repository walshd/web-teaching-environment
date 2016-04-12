# -*- coding: utf-8 -*-
u"""
##################################
:mod:`wte.doc` -- Docutils Helpers
##################################

The :mod:`~wte.doc` module contains helper functions for the docutils ReST
processing.

.. moduleauthor:: Mark Hall <mark.hall@mail.room3b.eu>
"""
import re

from docutils import nodes


def button_role(role, rawtext, text, node_id, inliner):
    u"""Handles adding the necessary inline styling to indicate buttons in the
    documentation."""
    if role == 'primary_btn':
        return [nodes.inline(rawtext, text, classes=['button'])], []
    elif role == 'secondary_btn':
        return [nodes.inline(rawtext, text, classes=['button', 'secondary'])], []
    elif role == 'alert_btn':
        return [nodes.inline(rawtext, text, classes=['button', 'alert'])], []
    else:
        return [], []


DROPDOWN_PATTERN = re.compile(r'(.+)(?:<(.+)>)')


def link_role(role, rawtext, text, node_id, inliner):
    u"""Handles adding the necessary inline styling to indicate links in the
    documentation."""
    if role == 'text_link':
        return [nodes.inline(rawtext, text, classes=['text-link'])], []
    elif role == 'topbar_link':
        return [nodes.inline(rawtext, text, classes=['topbar-link'])], []
    elif role == 'dropdown_link':
        match = re.match(DROPDOWN_PATTERN, text)
        if match:
            return [nodes.inline(rawtext, ' ' + match.group(1), classes=['dropdown-link', match.group(2)])], []
        else:
            return [nodes.inline(rawtext, text, classes=['dropdown-link'])], []
    else:
        return [], []


def icon_role(role, rawtext, text, node_id, inliner):
    return [nodes.inline(rawtext, '', classes=[text])], []


def setup(app):
    u"""Adds the new docutils roles to the docutils app
    """
    app.add_role('primary_btn', button_role)
    app.add_role('secondary_btn', button_role)
    app.add_role('alert_btn', button_role)
    app.add_role('text_link', link_role)
    app.add_role('topbar_link', link_role)
    app.add_role('dropdown_link', link_role)
    app.add_role('icon', icon_role)
