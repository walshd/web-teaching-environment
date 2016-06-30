# -*- coding: utf-8 -*-
"""
######################################################
:mod:`pywebtools.pyramid.decorators` -- Decoratorators
######################################################

The :mod:`~pywebtools.pyramid.decorators` module contains function decorators for use with
views.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from decorator import decorator
from pyramid.httpexceptions import HTTPMethodNotAllowed
from pywebtools.pyramid.util import request_from_args


def require_method(methods):
    """Checks that the current request method is in the list of ``methods``
    that are allowed for the given request.

    :param methods: The list of valid request methods
    :type methods: `list` of `unicode`
    """
    if not isinstance(methods, list):
        methods = [methods]

    def wrapper(f, *args, **kwargs):
        request = request_from_args(*args)
        if request.method in methods:
            return f(*args, **kwargs)
        else:
            raise HTTPMethodNotAllowed()
    return decorator(wrapper)
