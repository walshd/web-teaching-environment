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
from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools.auth import is_authorised
from sqlalchemy import and_

from wte.decorators import current_user
from . import (user, frontend, module, tutorial, page, exercise, template)

def init(config, settings):
    u"""Adds the following routes (route name, URL pattern, handler):
    
    * ``root`` -- ``/`` -- :func:`~wte.views.root`
    
    Then calls the ``init`` function on all modules within :mod:`~wte.views`
    """
    config.add_route('root', '/')

    user.init(config)
    module.init(config)
    tutorial.init(config)
    exercise.init(config)
    page.init(config)
    template.init(config)
    frontend.init(config)

@view_config(route_name='root')
@render({'text/html': 'root.html'})
@current_user()
def root(request):
    u"""Handles the ``/`` route.
    """
    return {}