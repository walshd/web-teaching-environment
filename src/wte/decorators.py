# -*- coding: utf-8 -*-
u"""
#######################################
:mod:`wte.decorators` -- Decoratorators
#######################################

The :mod:`~wte.decorators` module contains function decorators for use with
various functions.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from decorator import decorator
from pyramid.httpexceptions import HTTPMethodNotAllowed
from pywebtools.renderer import request_from_args

from wte.models import (DBSession, User)
from wte.util import unauthorised_redirect


def current_user():
    """Inserts the currently logged in :class:`~wte.models.User` into the
    `request` parameter under the attribute ``current_user``. If there is no
    logged in user, then an anonymous :class:`~wte.models.User` is created.

    Used in view functions.
    """
    def wrapper(f, *args, **kwargs):
        request = request_from_args(*args)
        if 'uid' in request.session:
            dbsession = DBSession()
            user = dbsession.query(User).filter(User.id == request.session['uid']).first()
            if user:
                user.logged_in = True
                request.current_user = user
            else:
                request.current_user = User('anonymous@example.com', 'Anonymous')
                request.current_user.logged_in = False
        else:
            request.current_user = User('anonymous@example.com', 'Anonymous')
            request.current_user.logged_in = False
        return f(*args, **kwargs)
    return decorator(wrapper)


def require_logged_in():
    u"""Checks that the current user is logged in, otherwise redirects to the login
    page. Requires that the :func:`~wte.decorators.current_user` decorator is run
    first.
    """
    def wrapper(f, *args, **kwargs):
        request = request_from_args(*args)
        if request.current_user.logged_in:
            return f(*args, **kwargs)
        else:
            unauthorised_redirect(request,
                                  message=u'You must log-in or register to access this area')
    return decorator(wrapper)


def require_method(methods):
    u"""Checks that the current request method is in the list of ``methods``
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
