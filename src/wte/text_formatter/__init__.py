# -*- coding: utf-8 -*-
"""
#########################
:mod:`wte.text_formatter`
#########################

This module contains functions for formatting the instruction texts shown to
the student.

.. moduleauthor:: Mark Hall <mark.hall@mail.room3b.eu>
"""
from copy import deepcopy
from docutils import core
from docutils.writers import html4css1

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


def compile_rst(text, request, part=None, line_numbers=False):
    """Compiles the given ReStructuredText into HTML. Returns only the actual
    content of the generated HTML document, without headers or footers.

    :param text: The ReST to compile
    :type text: `unicode`
    :param line_numbers: Whether to generate a "data-source-ln" attribute with
                         source line-numbers (default: ``false``)
    :type line_numbers: ``boolean``
    :return: The body content of the generated HTML
    :return_type: `unicode`
    """
    settings = deepcopy(SETTINGS)
    settings['pyramid_request'] = request
    settings['wte_part'] = part
    writer = html4css1.Writer()
    if line_numbers:
        writer.translator_class = HTMLLineNumbersTranslator
    parts = core.publish_parts(source=text, writer=writer, settings_overrides=settings)
    return parts['body']


class HTMLLineNumbersTranslator(html4css1.HTMLTranslator):
    """The :class:`~wte.text_formatter.HTMLLineNumbersTranslator` extends the
    :class:`html4css1.HTMLTranslator`, outputting source line numbers for all
    nodes that have one.
    """

    def starttag(self, node, tagname, suffix='\n', empty=False, **attributes):
        """
        Construct and return a start tag given a node (id & class attributes
        are extracted), tag name, and optional attributes.
        """
        tagname = tagname.lower()
        prefix = []
        atts = {}
        ids = []
        for (name, value) in list(attributes.items()):
            atts[name.lower()] = value
        classes = []
        languages = []
        # unify class arguments and move language specification
        for cls in node.get('classes', []) + atts.pop('class', '').split():
            if cls.startswith('language-'):
                languages.append(cls[9:])
            elif cls.strip() and cls not in classes:
                classes.append(cls)
        if languages:
            # attribute name is 'lang' in XHTML 1.0 but 'xml:lang' in 1.1
            atts[self.lang_attribute] = languages[0]
        if classes:
            atts['class'] = ' '.join(classes)
        assert 'id' not in atts
        ids.extend(node.get('ids', []))
        if 'ids' in atts:
            ids.extend(atts['ids'])
            del atts['ids']
        if ids:
            atts['id'] = ids[0]
            for id in ids[1:]:
                # Add empty "span" elements for additional IDs.  Note
                # that we cannot use empty "a" elements because there
                # may be targets inside of references, but nested "a"
                # elements aren't allowed in XHTML (even if they do
                # not all have a "href" attribute).
                if empty:
                    # Empty tag.  Insert target right in front of element.
                    prefix.append('<span id="%s"></span>' % id)
                else:
                    # Non-empty tag.  Place the auxiliary <span> tag
                    # *inside* the element, as the first child.
                    suffix += '<span id="%s"></span>' % id
        if node.line:
            atts['data-source-ln'] = node.line
        attlist = list(atts.items())
        attlist.sort()
        parts = [tagname]
        for name, value in attlist:
            # value=None was used for boolean attributes without
            # value, but this isn't supported by XHTML.
            assert value is not None
            if isinstance(value, list):
                values = [str(v) for v in value]
                parts.append('%s="%s"' % (name.lower(),
                                          self.attval(' '.join(values))))
            else:
                parts.append('%s="%s"' % (name.lower(),
                                          self.attval(str(value))))
        if empty:
            infix = ' /'
        else:
            infix = ''
        return ''.join(prefix) + '<%s%s>' % (' '.join(parts), infix) + suffix
