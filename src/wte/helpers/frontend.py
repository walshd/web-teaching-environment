# -*- coding: utf-8 -*-
u"""
###############################################################
:mod:`wte.helpers.frontend` -- Helpers for the frontend display
###############################################################

The :mod:`~wte.helpers.frontend` module provides helper functionality used to
render the frontend page displays.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import json
import re

from genshi.builder import tag, Markup


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
                    'text/javascript': ['javascript'],
                    'text/x-rst': ['python', 'stex', ('../addon/mode', 'overlay'), 'rst']}


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
            for mode in CODEMIRROR_MODES[mimetype]:
                if isinstance(mode, tuple):
                    modes.append(mode)
                else:
                    modes.append((mode, mode))
            #modes.extend(CODEMIRROR_MODES[mimetype])
    return tag([tag.script(src=request.static_url('wte:static/js/codemirror/mode/%s/%s.js' % mode))
                for mode in modes])


def page_pagination(request, part):
    u"""Generates the pagination UI for the individual page display of a
    :class:`~wte.models.Part`.

    :param request: The current request
    :type request: :class:`~pyramid.request.Request`
    :param part: The current parte to display pagination for
    :type part: :class:`~wte.models.Part`
    :return: The resulting HTML markup
    """
    prev_page = None
    next_page = None
    state = 0
    for child in part.parent.children:
        if state == 0 and child != part:
            prev_page = child
        elif state == 0 and child == part:
            state = 1
        elif state == 1:
            next_page = child
            break
    items = []
    if prev_page:
        items.append(tag.li(tag.a(Markup('&laquo; Previous page'),
                                  href=request.route_url('part.view',
                                                         pid=prev_page.id))))
    else:
        items.append(tag.li(Markup('&laquo; Previous page'),
                            class_='disabled'))
    if next_page:
        items.append(tag.li(tag.a(Markup('Next page &raquo;'),
                                  href=request.route_url('part.view',
                                                         pid=next_page.id))))
    else:
        items.append(tag.li(Markup('Previous page &raquo;'),
                            class_='disabled'))
    return tag.ul(items,
                  class_='pagination')


def primary_filename(progress):
    u"""Returns the filename of the first :class:`~wte.models.File` from the
    :class:`~wte.models.UserPartProgress` that has the mimetype "text/html".

    :param progress: The :class:`~wte.models.UserPartProgress` to get the files
                     from
    :type progress: :class:`~wte.models.UserPartProgress`
    :return: The filename as a string or the empty string
    :rtype: `unicode`
    """
    files = [f for f in progress.files if f.mimetype == 'text/html']
    if files:
        return files[0].filename
    else:
        return ''


def confirm_delete(obj_type, title, has_parts=False):
    u"""Generates the confirmation JSON object for use with the jQuery.postLink() plugin.

    :param obj_type: The type of object that is being deleted
    :type obj_type: ``unicode``
    :param title: The title of the object that is being delete
    :type title: ``unicode``
    :param has_parts: Whether to add the suffix " and all its parts"
    :type has_parts: ``bool``
    :return: JSON object
    :rtype: ``unicode``
    """
    msg = 'Please confirm that you wish to delete the %s "%s"' % (obj_type, title)
    if has_parts:
        msg = '%s and all its parts.' % (msg)
    else:
        msg = '%s.' % (msg)
    options = {'title': 'Delete this %s' % (obj_type),
               'msg': msg,
               'cancel': {'label': "Don't delete"},
               'ok': {'label': 'Delete',
                      'class_': 'alert'}}
    return json.dumps(options)


def part_summary(part):
    u"""Generates summary text for a :class:`~wte.models.Part` by extracting the first HTML element
    from the ``compiled_content``. Due to the use of ReST, this should in most cases be the first
    paragraph.

    :param part: The :class:`~wte.models.Part` to generate the summary for
    :type part: :class:`~wte.models.Part`
    :return: The first HTML element
    :rtype: :class:`~genshi.builder.Markup`
    """
    content = part.compiled_content
    if content:
        m = re.search(r'<([a-zA-Z+])>', content)
        if m:
            start = content.find('<%s>' % (m.group(1)))
            end = content.find('</%s>' % (m.group(1))) + len(m.group(1)) + 3
            return Markup(content[start:end])
    return None
