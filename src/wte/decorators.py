# -*- coding: utf-8 -*-
"""
#######################################
:mod:`wte.decorators` -- Decoratorators
#######################################

The :mod:`~wte.decorators` module contains function decorators for use with
various functions.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from decorator import decorator
from pyramid.httpexceptions import HTTPMethodNotAllowed
from pywebtools.pyramid.util import request_from_args

from wte.util import unauthorised_redirect


def require_logged_in():
    """Checks that the current user is logged in, otherwise redirects to the login
    page. Requires that the :func:`~wte.decorators.current_user` decorator is run
    first.
    """
    def wrapper(f, *args, **kwargs):
        request = request_from_args(*args)
        if request.current_user.logged_in:
            return f(*args, **kwargs)
        else:
            unauthorised_redirect(request,
                                  message='You must log-in or register to access this area')
    return decorator(wrapper)


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
