# -*- coding: utf-8 -*-
u"""
#################################
:mod:`wte.views` -- View handlers
#################################

The :mod:`~wte.views` package contains the view handlers that implement the
majority of the Web Teaching Environment's functionality.

Each module within :mod:`~wte.views` contains an ``init`` function that
initialises the routes that are handled by that module.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from mimetypes import guess_type
from pkg_resources import resource_string
from pyramid.httpexceptions import HTTPNotFound, HTTPSeeOther
from pyramid.view import view_config
from pyramid.response import Response

from wte.decorators import current_user
from . import (user, part, asset, user_role, timed_tasks, admin)


def init(config, settings):
    u"""Adds the following routes (route name, URL pattern, handler):

    * ``root`` -- ``/`` -- :func:`~wte.views.root`

    Then calls the ``init`` function on all modules within :mod:`~wte.views`
    """
    config.add_route('root', '/')
    config.add_route('help', '/help/*path')

    admin.init(config)
    user.init(config)
    part.init(config)
    asset.init(config)
    user_role.init(config)
    timed_tasks.init(config)


@view_config(route_name='root', renderer='wte:templates/root.kajiki')
@current_user()
def root(request):
    u"""Handles the ``/`` route.
    """
    return {}


@view_config(route_name='help')
def help_page(request):
    """Handles the ``/help`` route, displaying the appropriate help page.
    """
    url = 'templates/help/%s' % '/'.join(request.matchdict['path'])
    if url.endswith('/'):
        url = '%sindex.html' % url
    if url.endswith('.html') and 'user' not in url:
        raise HTTPSeeOther(request.route_url('help', path=['user', 'index.html']))
    try:
        mimetype = guess_type(url)
        if mimetype:
            mimetype = mimetype[0]
        else:
            mimetype = 'unknown/unknown'
        return Response(resource_string('wte', url),
                        content_type=mimetype)
    except:
        raise HTTPNotFound()


@view_config(context=HTTPNotFound, renderer='wte:templates/errors/404.kajiki')
@current_user()
def notfound_404(request):
    u"""Handles 404 errors
    """
    return {'crumbs': [{'title': 'Not Found'}]}


@view_config(context=Exception, renderer='wte:templates/errors/500.kajiki')
@current_user()
def servererror_500(request):
    u"""Handles 500 errors
    """
    return {'crumbs': [{'title': 'Internal Server Error'}]}
