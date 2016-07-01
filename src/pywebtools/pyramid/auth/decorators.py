# -*- coding: utf-8 -*-
u"""
######################################################
:mod:`pywebtools.pyramid.decorators` -- Decoratorators
######################################################

The :mod:`~pywebtools.pyramid.auth.decorators` module contains function decorators for
use with the authentication framework.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from decorator import decorator

from pyramid.httpexceptions import HTTPNotFound, HTTPSeeOther

from pywebtools.pyramid.auth.models import User
from pywebtools.pyramid.util import request_from_args
from pywebtools.sqlalchemy import DBSession


def unauthorised_redirect(request, redirect_to=None, message=None):
    """Provides standardised handling of "unauthorised" redirection. Depending
    on whether the user is currently logged in, it will set the appropriate
    error message into the session flash and redirect to the appropriate page.
    If the user is logged in, it will redirect to the root page or to the
    ``redirect_to`` URL if specified. If the user is not logged in, it will
    always redirect to the login page.

    :param request: The pyramid request
    :param redirect_to: The URL to redirect to, if the user is currently
                        logged in.
    :type redirect_to: `unicode`
    :param message: The message to show to the user
    :type message: ``unicode``
    """
    if request.current_user.logged_in:
        if message:
            request.session.flash(message, queue='auth')
        else:
            request.session.flash('You are not authorised to access this area.', queue='auth')
        if redirect_to:
            raise HTTPSeeOther(redirect_to)
        else:
            raise HTTPSeeOther(request.route_url('root'))
    else:
        if message:
            request.session.flash(message, queue='auth')
        else:
            request.session.flash('Please log in to access this area.', queue='auth')
        raise HTTPSeeOther(request.route_url('user.login', _query={'return_to': request.current_route_url()}))


def current_user():
    """Inserts the currently logged in :class:`~pywebtools.pyramid.auth.models.User` into the
    `request` parameter under the attribute ``current_user``. If there is no
    logged in user, then an anonymous :class:`~pywebtools.pyramid.auth.models.User` is created.

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
                request.current_user = User()
                request.current_user.logged_in = False
        else:
            request.current_user = User()
            request.current_user.logged_in = False
        return f(*args, **kwargs)
    return decorator(wrapper)


def require_permission(permission=None, class_=None, request_key=None, action=None):
    """Checks whether the current user has the given permission. Supports two modes:

    If you provide the ``permission`` parameter and it will use
    :func:`~pywebtools.pyramid.auth.models.User.has_permission` to check whether the
    current user has the given permission. If not, it raises
    :class:`~pyramid.httpexceptions.HTTPUnauthorised`.

    Alternatively if you provide ``class_``, ``request_key``, and ``action`` parameters
    it will run a SQLAlchemy query for the ``class_``, filtering
    ``class_.id == request.matchdict[request_key]``. If that returns a result, then it
    will use the ``class_``\ 's ``allow`` to check whether the current user is allowed
    to perform the given ``action``. If not  it raises
    :class:`~pyramid.httpexceptions.HTTPUnauthorised`. If no result is returned then it
    will raise :class:`~pyramid.httpexceptions.HTTPNotFound`.

    :param permission: The permission to check the user for
    :type permission: ``str``
    :param class_: The SQLAlchemy ORM class to use for finding the instance that matches
                   the ``request_key`` value
    :type class_: ``class``
    :param request_key: The key to use for getting a unique identifier from the
                        ``request.matchdict`` to use in finding an instance of ``class_``
    :type request_key: ``str``
    :param action: The action to check for with the instance of ``class_``
    :type action: ``str``
    :return: The decorated function's return value
    """
    def wrapper(f, *args, **kwargs):
        request = request_from_args(*args)
        if request.current_user is not None:
            if permission is not None:
                if request.current_user.has_permission(permission):
                    return f(*args, **kwargs)
                else:
                    unauthorised_redirect(request)
            elif object is not None and request_key is not None and action is not None:
                dbsession = DBSession()
                instance = dbsession.query(class_).filter(class_.id == request.matchdict[request_key]).first()
                if instance is not None:
                    if instance.allow(action, request.current_user):
                        return f(*args, **kwargs)
                    else:
                        unauthorised_redirect(request)
                else:
                    raise HTTPNotFound()
            else:
                return f(*args, **kwargs)
        else:
            unauthorised_redirect(request)
    return decorator(wrapper)


def require_logged_in():
    """Checks that the current user is logged in, otherwise redirects to the login
    page. Requires that the :func:`~pywebtools.pyramid.auth.decorators.current_user` decorator is run
    first.
    """
    def wrapper(f, *args, **kwargs):
        request = request_from_args(*args)
        if request.current_user.logged_in:
            return f(*args, **kwargs)
        else:
            unauthorised_redirect(request)
    return decorator(wrapper)
