# -*- coding: utf-8 -*-
u"""

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from genshi.builder import tag
from pywebtools import form as tags

def field(name, label, form_tag, size=None, e=None, **kwargs):
    """Generates the HTML form field code around a given form tag. To generate
    the actual form tag, it calls the function passed into the ``form_tag``
    parameter. The ``form_tag`` parameter is passed all extra keyword
    parameters.
    
    :param name: The form field's name
    :type name: `unicode`
    :param label: The form field's label
    :type label: `unicode`
    :param form_tag: The function to call to generate the actual form tag
    :type form_tag: `callable`
    :param size: The column size
    :type size: `unicode`
    :param e: The error object
    :type e: :class:`~formencode.api.Invalid`
    :param kwargs: Any keyword arguments to pass to `form_tag`
    """ 
    if size:
        field_class = '%s column %s' % (size, kwargs['class_']) if 'class_' in kwargs else '%s column' % (size)
        column_class = '%s column' % (size)
    else:
        field_class = kwargs['class_'] if 'class_' in kwargs else ''
        column_class = ''
    elements = [label]
    if e and e.error_dict and name in e.error_dict:
        field_class = '%s' % (field_class)
        column_class = '%s' % (column_class)
    if 'class_' in kwargs:
        del kwargs['class_']
    elements.append(form_tag(name, e=None, class_=field_class, **kwargs))
    if e and e.error_dict and name in e.error_dict:
        elements.append(tag.span(e.unpack_errors()[name], class_='error'))
        label = tag.label(elements, class_='error')
    else:
        label = tag.label(elements)
    return tag.div(label, class_=column_class)
