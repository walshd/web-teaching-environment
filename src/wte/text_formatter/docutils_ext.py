# -*- coding: utf-8 -*-
"""
######################################
:mod:`wte.text_formatter.docutils_ext`
######################################

This module contains docutils extensions (roles and directives) that provide
the additional formatting support required by the
:func:`~wte.text_formatter.compile_rst` function.
"""
import re

from docutils import nodes, utils
from docutils.parsers.rst import directives, roles, Directive
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer, get_all_lexers
from sqlalchemy import and_

from wte.models import (DBSession, Asset, Part)


def init(settings):
    """Initialise and load the docutils extensions.
    """
    directives.register_directive('sourcecode', Pygments)
    roles.register_local_role('asset', asset_ref_role)
    roles.register_local_role('crossref', crossref_role)
    for _, aliases, _, _ in get_all_lexers():
        for alias in aliases:
            roles.register_local_role('code-%s' % (alias), inline_pygments_role)


class HtmlTitleFormatter(HtmlFormatter):
    """The :class:`~wte.text_formatter.docutils_ext.HtmlTitleFormatter` is
    an extension of :class:`pygments.formatters.HtmlFormatter` that supports
    adding the optional language name and filename to the top of the code
    block.
    """
    def __init__(self, language=None, filename=None, **kwargs):
        HtmlFormatter.__init__(self, **kwargs)
        self.language = language
        self.filename = filename

    def wrap(self, source, outfile):
        return self._wrap_code(source)

    def _wrap_code(self, source):
        yield 0, '<div class="source panel %s">' % (self.language if self.language else '')
        if self.language:
            yield 0, '<div class="title"><span class="main">%s</span>' % (self.language)
            if self.filename:
                yield 0, '<span class="filename">%s</span>' % (self.filename)
            yield 0, '</div><pre>'
        for i, t in source:
            yield i, t
        yield 0, '</pre></div>'


class Pygments(Directive):
    """The Pygments reStructuredText directive

    This fragment is a Docutils_ 0.5 directive that renders source code
    (to HTML only, currently) via Pygments.

    To use it, adjust the options below and copy the code into a module
    that you import on initialization.  The code then automatically
    registers a ``sourcecode`` directive that you can use instead of
    normal code blocks like this::

        .. sourcecode:: python

            My code goes here.

    If you want to have different code styles, e.g. one with line numbers
    and one without, add formatters with their names in the VARIANTS dict
    below.  You can invoke them instead of the DEFAULT one by using a
    directive option::

        .. sourcecode:: python
            :linenos:

            My code goes here.

    Look at the `directive documentation`_ to get all the gory details.

    .. _Docutils: http://docutils.sf.net/
    .. _directive documentation:
       http://docutils.sourceforge.net/docs/howto/rst-directives.html

    :copyright: Copyright 2006-2014 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
    """
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'filename': directives.unchanged}
    has_content = True

    def run(self):
        self.assert_has_content()
        try:
            lexer = get_lexer_by_name(self.arguments[0])
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()
        # take an arbitrary option if more than one is given
        formatter = HtmlTitleFormatter(language=lexer.name,
                                       filename=self.options['filename'] if 'filename' in self.options else None,
                                       noclasses=False,
                                       style='native',
                                       cssclass=u'source %s' % (lexer.name))
        parsed = highlight(u'\n'.join(self.content), lexer, formatter)
        return [nodes.raw('', parsed, format='html')]


CROSSREF_PATTERN = re.compile(r'([0-9]+)|(?:(.*)<([0-9]+)>)')


def crossref_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """The :func:`~wte.text_formatter.docutils_ext.crossref_role` function
    implements an additional docutils role that handles cross-references
    between :class:`~wte.models.Part`\ s.

    Usage in ReST is \:crossref\:\`part_id\` or \:crossref\:\`link text
    <part_id>\`.
    """
    from wte.models import (DBSession, Part)
    request = inliner.document.settings.pyramid_request
    result = []
    messages = []
    text = utils.unescape(text)
    match = re.match(CROSSREF_PATTERN, text)
    if match:
        groups = match.groups()
        target_id = groups[0] if groups[0] else groups[2]
        dbsession = DBSession()
        part = dbsession.query(Part).filter(Part.id == target_id).first()
        if part:
            result.append(nodes.reference(rawtext, groups[1] if groups[1] else part.title,
                                          internal=False,
                                          refuri=request.route_url('part.view',
                                                                   pid=target_id)))
        else:
            messages.append(inliner.reporter.warning('There is no target to link to for "%s"' % (text), line=lineno))
            result.append(inliner.problematic(rawtext, rawtext, messages[0]))
    else:
        messages.append(inliner.reporter.error('No valid link target identifier could be identified in "%s"' % (text),
                                               line=lineno))
        result.append(inliner.problematic(rawtext, rawtext, messages[0]))
    return result, messages


def inline_pygments_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """The :func:`~wte.text_formatter.docutils_ext.inline_pygments_role`
    function provides a docutils role that handles inline code highlighting
    using Pygments. The name of the language to use for highlighting is taken
    from the name of the role (which must be formatted ``code-language_name`.
    """
    try:
        lexer = get_lexer_by_name(name[5:])
    except ValueError:
        lexer = TextLexer()
    formatter = HtmlFormatter(nowrap=True)
    parsed = highlight(text, lexer, formatter)
    return [nodes.raw('', '<span class="source">%s</span>' % (parsed), format='html')], []


ASSET_PATTERN = re.compile(r'((?:(parent):)?([a-zA-Z0-9_\-.]+)$)|((.+)(?:<(?:(parent):)?([a-zA-Z0-9_\-.]+)>)$)')


def asset_ref_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """The :func:`~wte.text_formatter.docutils_ext.asset_ref_role` functio
    provides a docutils role that handles linking in :class:`~wte.models.Asset`
    into the text. If the :class:`~wte.models.Asset` is an image, then the
    image is loaded inline, otherwise a download link for all other types
    of :class:`~wte.models.Asset` is created.
    """
    result = []
    messages = []
    settings = inliner.document.settings
    request = settings.pyramid_request
    if hasattr(settings, 'wte_part') and settings.wte_part:
        dbsession = DBSession()
        match = re.match(ASSET_PATTERN, text)
        if match:
            groups = match.groups()
            if groups[0]:
                title = None
                parent = groups[1] == 'parent'
                filename = groups[2]
            else:
                title = groups[4]
                parent = groups[5] == 'parent'
                filename = groups[6]
            part_id = settings.wte_part.parent_id if parent else settings.wte_part.id
            asset = dbsession.query(Asset).join(Asset.parts).filter(and_(Part.id == part_id,
                                                                         Asset.filename == filename)).first()
            if asset:
                if asset.mimetype.startswith('image/'):
                    result.append(nodes.image(rawtext,
                                              uri=request.route_url('asset.view',
                                                                    pid=part_id,
                                                                    filename=asset.filename),
                                              alt=title))
                else:
                    result.append(nodes.reference(rawtext,
                                                  title if title else asset.filename,
                                                  internal=False,
                                                  refuri=request.route_url('asset.view',
                                                                           pid=part_id,
                                                                           filename=asset.filename,
                                                                           _query=[('download', 'true')])))
            else:
                messages.append(inliner.reporter.error('No asset found for the filename "%s"' % (filename),
                                                       line=lineno))
        else:
            messages.append(inliner.reporter.error('No asset found for the filename "%s"' % (text),
                                                   line=lineno))
    else:
        messages.append(inliner.reporter.error('Internal error: no part set',
                                               line=lineno))

    return result, messages
