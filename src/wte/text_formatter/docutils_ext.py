# -*- coding: utf-8 -*-
"""
######################################
:mod:`wte.text_formatter.docutils_ext`
######################################

This module contains docutils extensions (roles and directives) that provide
the additional formatting support required by the
:func:`~wte.text_formatter.compile_rst` function.
"""
import json
import re

from docutils import nodes, utils
from docutils.parsers.rst import directives, roles, Directive
from docutils.writers.html4css1 import HTMLTranslator
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer, get_all_lexers
from pywebtools.sqlalchemy import DBSession
from sqlalchemy import and_

from wte.models import (Asset, Part)


def init(settings):
    """Initialise and load the docutils extensions.
    """
    directives.register_directive('sourcecode', Pygments)
    directives.register_directive('youtube', YouTube)
    directives.register_directive('quiz', Quiz)
    directives.register_directive('quiz-question', QuizQuestion)
    roles.register_local_role('asset', asset_ref_role)
    roles.register_local_role('crossref', crossref_role)
    roles.register_local_role('style', inline_css_role)
    for _, aliases, _, _ in get_all_lexers():
        for alias in aliases:
            roles.register_local_role('code-%s' % (alias), inline_pygments_role)
    nodes._add_node_class_names([HtmlElementBlock.__name__])
    setattr(HTMLTranslator, 'visit_%s' % HtmlElementBlock.__name__, visit_htmlelementblock)
    setattr(HTMLTranslator, 'depart_%s' % HtmlElementBlock.__name__, depart_htmlelementblock)


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
        yield 0, '<div class="source panel %s">' % (self.language.replace(' ', '') if self.language else '')
        if self.language:
            yield 0, '<div class="title"><span class="main">%s</span>' % (self.language)
            if self.filename:
                yield 0, '<span class="filename">%s</span>' % (self.filename)
            yield 0, '</div><pre>'
        for i, t in source:
            yield i, t
        yield 0, '</pre></div>'


def flag_bool_option(value):
    """Options conversion function for ReST
    :class:`~docutils.parser.rst.Directive` that returns ``True`` if the
    value is set and has any value except "false".
    """
    if str(value).lower() != 'false':
        return True
    else:
        return False


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
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {'filename': directives.unchanged,
                   'startinline': flag_bool_option,
                   'linenos': int}
    has_content = True

    def run(self):
        self.assert_has_content()
        try:
            lexer = get_lexer_by_name(self.arguments[0], **self.options)
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()
        # take an arbitrary option if more than one is given
        formatter = HtmlTitleFormatter(language=lexer.name,
                                       filename=self.options['filename'] if 'filename' in self.options else None,
                                       noclasses=False,
                                       style='native',
                                       cssclass='source %s' % (lexer.name),
                                       linenos='inline' if 'linenos' in self.options else False,
                                       linenostart=self.options['linenos'] if 'linenos' in self.options else 1)
        parsed = highlight('\n'.join(self.content), lexer, formatter)
        return [nodes.raw('', parsed, format='html')]


YOUTUBE_BASE_TEMPLATE = '<iframe width="560" height="315" ' + \
    'src="%s" allowfullscreen="allowfullscreen"></iframe>'


class YouTube(Directive):
    """The :class:`~wte.text_formatter.docutils_ext.YouTube` directive enables
    support for embeddeding YouTube videos in ReST. It takes a single parameter
    that is the YouTube URL to embed::

      .. youtube:: https://URL/TO/VIDEO

    """
    required_arguments = 1

    def run(self):
        return [nodes.raw('', YOUTUBE_BASE_TEMPLATE % (self.arguments[0]), format='html')]


CROSSREF_PATTERN = re.compile(r'([0-9]+)|(?:(.*)<([0-9]+)>)')


def crossref_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """The :func:`~wte.text_formatter.docutils_ext.crossref_role` function
    implements an additional docutils role that handles cross-references
    between :class:`~wte.models.Part`\ s.

    Usage in ReST is \:crossref\:\`part_id\` or \:crossref\:\`link text
    <part_id>\`.
    """
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
    from the name of the role (which must be formatted ``code-language_name``).
    """
    try:
        lexer = get_lexer_by_name(name[5:])
    except ValueError:
        lexer = TextLexer()
    formatter = HtmlFormatter(nowrap=True)
    text = text.replace('\x00', '')
    parsed = highlight(text, lexer, formatter)
    return [nodes.raw('', '<span class="source">%s</span>' % (parsed), format='html')], []


ASSET_PATTERN = re.compile(r'((?:(parent):)?([a-zA-Z0-9_\-.]+)$)|((.+)(?:<(?:(parent):)?([a-zA-Z0-9_\-.]+)>)$)')


def asset_ref_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """The :func:`~wte.text_formatter.docutils_ext.asset_ref_role` function
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
                filename = groups[2]
            else:
                title = groups[4]
                filename = groups[6]
            part_ids = []
            part = settings.wte_part
            while part is not None:
                part_ids.append(part.id)
                part = part.parent
            data = dbsession.query(Asset, Part).join(Asset.parts).filter(and_(Part.id.in_(part_ids),
                                                                              Asset.filename == filename)).first()
            if data:
                asset, part = data
                if asset.mimetype.startswith('image/'):
                    result.append(nodes.image(rawtext,
                                              uri=request.route_url('asset.view',
                                                                    pid=part.id,
                                                                    filename=asset.filename),
                                              alt=title if title else asset.filename))
                else:
                    result.append(nodes.reference(rawtext,
                                                  title if title else asset.filename,
                                                  internal=False,
                                                  refuri=request.route_url('asset.view',
                                                                           pid=part.id,
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


CSS_PATTERN = re.compile(r'(.+)<([a-zA-Z0-9_\-.:;#]+)>$')


def inline_css_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """The :func:`~wte.text_formatter.docutils_ext.inline_css_role` function
    provides a docutils role that allows for the specification of arbitrary CSS
    that is then assigned to a <span> element.
    """
    result = []
    messages = []
    match = re.match(CSS_PATTERN, text)
    if match:
        result.append(nodes.raw('', '<span style="%s">%s</span>' % (match.group(2), match.group(1)), format='html'))
    else:
        messages.append(inliner.reporter.error('No CSS definition found in "%s"' % (text)))
    return result, messages


class HtmlElementBlock(nodes.General, nodes.Element):
    """The :class:`~wte.text_formatter.docutils_ext.HtmlElementBlock` is a docutils node
    for generating arbitrary HTML elements.

    The HTML element to generate can be configured by setting ``html_element`` on the node.
    HTML attributes can be configured by setting the ``html_attributes`` property on the node,
    which must be set to a ``dict``.
    """
    pass


def visit_htmlelementblock(self, node):
    """Visitor for the :class:`~wte.text_formatter.docutils_ext.HtmlElementBlock` to generate
    the actual HTML output.
    """
    if hasattr(node, 'html_element'):
        element_name = node.html_element
    else:
        element_name = 'div'
    if hasattr(node, 'html_attributes'):
        attrs = node.html_attributes
    else:
        attrs = {}
    self.body.append(self.starttag(node, element_name, **attrs))


def depart_htmlelementblock(self, node):
    """Visitor exit for the :class:`~wte.text_formatter.docutils_ext.HtmlElementBlock`.
    """
    if hasattr(node, 'html_element'):
        element_name = node.html_element
    else:
        element_name = 'div'
    self.body.append('</%s>\n' % element_name)


class Quiz(Directive):
    """The :class:`~wte.text_formatter.docutils_ext.Quiz` is a directive to generate
    the outer wrapper for an in-part quiz. It takes a single required parameter that
    is the identifier for the quiz in the current :class:`~wte.models.Part`. An optional
    ``title`` parameter is the title of the quiz to show to the user. The actual
    questions need to be provided via :class:`~wte.text_formatter.docutils_ext.QuizAnswer`::

      .. quiz: quiz_identifier
         :title: This is a Quiz!

         .. quiz-question: question1
            :question: Is this right?

            [x] Answer 1
            Answer 2
            Answer 3
    """
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {'title': directives.unchanged}
    has_content = True

    def run(self):
        node = nodes.Element()
        node.document = self.state.document
        self.state.nested_parse(self.content, self.content_offset, node)
        quiz = HtmlElementBlock()
        quiz.html_element = 'form'
        quiz.html_attributes = {'class': 'quiz',
                                'action': '',
                                'data-quiz-id': self.arguments[0]}
        if 'title' in self.options:
            heading = HtmlElementBlock()
            heading.html_attributes = {'class': 'title'}
            heading.append(nodes.paragraph(self.options['title'], self.options['title']))
            quiz.append(heading)
        quiz.extend(node)
        buttons = HtmlElementBlock()
        buttons.html_attributes = {'class': 'text-right'}
        clear_button = HtmlElementBlock()
        clear_button.html_element = 'input'
        clear_button.html_attributes = {'type': 'reset',
                                        'value': 'Clear Answers',
                                        'class': 'button secondary'}
        buttons.append(clear_button)
        submit_button = HtmlElementBlock()
        submit_button.html_element = 'input'
        submit_button.html_attributes = {'type': 'submit',
                                         'value': 'Check Answers',
                                         'class': 'button'}
        buttons.append(submit_button)
        quiz.append(buttons)
        return [quiz]


class QuizQuestion(Directive):
    """The :class:`~wte.text_formatter.docutils_ext.QuizQuestion` generates a single
    question output. It takes a single required parameter that is the identifier for
    the question. An optional ``question`` parameter can be used to give the question's
    title. An optional ``type`` parameter can be used to specify whether single ("single-choice")
    or multiple choices ("multi-choice") are available::
    
      .. quiz-question:: question_id
         :question: Is this right?
         :type: single-choice
         
         [x]Answer 1
         [x]Answer 2
         Answer 3

    Each line of content represents one answer. The correct answers must be pre-fixed with
    "[x]". 
    """
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {'question': directives.unchanged,
                   'type': directives.unchanged}
    has_content = True

    def run(self):
        question = HtmlElementBlock()
        question.html_element = 'section'
        question.html_attributes = {'class': 'question',
                                    'data-question-id': self.arguments[0],
                                    'data-answers': json.dumps([a.replace('[x]', '').strip() for a in self.content if '[x]' in a])}
        if 'question' in self.options:
            heading = HtmlElementBlock()
            heading.html_attributes = {'class': 'title'}
            heading.append(nodes.paragraph(self.options['question'], self.options['question']))
            question.append(heading)
        for answer_source in self.content:
            answer_source = answer_source.replace('[x]', '').strip()
            answer = HtmlElementBlock()
            answer.html_element = 'label'
            input_element = HtmlElementBlock()
            input_element.html_element = 'input'
            input_element.html_attributes = {'type': 'radio' if 'type' not in self.options or self.options['type'] == 'single-choice' else 'checkbox',
                                             'value': answer_source,
                                             'name': self.arguments[0]}
            answer.append(input_element)
            answer.append(nodes.inline(answer_source, answer_source))
            question.append(answer)
        return [question]
