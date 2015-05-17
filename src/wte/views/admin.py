# -*- coding: utf-8 -*-
u"""

.. moduleauthor:: Mark Hall <mark.hall@mail.room3b.eu>
"""
from pyramid.view import view_config
from pywebtools.renderer import render

from wte.decorators import (current_user, require_logged_in)
from wte.util import unauthorised_redirect


def init(config):
    config.add_route('admin', '/admin')


@view_config(route_name='admin')
@render({'text/html': 'admin/index.html'})
@current_user()
@require_logged_in()
def admin(request):
    if request.current_user.has_permission('admin'):
        return {}
    else:
        raise unauthorised_redirect(request)
