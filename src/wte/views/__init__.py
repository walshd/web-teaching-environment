# -*- coding: utf-8 -*-

from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools.auth import is_authorised
from sqlalchemy import and_

from wte.decorators import current_user
from . import user, frontend

def init(config, settings):
    config.add_route('root', '/')

    user.init(config)

@view_config(route_name='root')
@render({'text/html': 'root.html'})
@current_user()
def users(request):
    return {}