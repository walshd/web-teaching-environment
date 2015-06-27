# -*- coding: utf-8 -*-
u"""

.. moduleauthor:: Mark Hall <mark.hall@mail.room3b.eu>
"""
import transaction

from pyramid.httpexceptions import HTTPSeeOther
from pyramid.view import view_config
from pywebtools.renderer import render

from wte.decorators import (current_user, require_logged_in)
from wte.models import (DBSession, Part)
from wte.text_formatter import compile_rst
from wte.util import unauthorised_redirect


def init(config):
    config.add_route('admin', '/admin')
    config.add_route('admin.content', '/admin/content')
    config.add_route('admin.content.regenerate', '/admin/content/regenerate')


@view_config(route_name='admin')
@render({'text/html': 'admin/index.html'})
@current_user()
@require_logged_in()
def admin(request):
    if request.current_user.has_permission('admin'):
        return {'crumbs': [{'title': 'Administration',
                            'url': request.current_route_url(),
                            'current': True}]}
    else:
        raise unauthorised_redirect(request)


@view_config(route_name='admin.content')
@render({'text/html': 'admin/content.html'})
@current_user()
@require_logged_in()
def content_admin(request):
    if request.current_user.has_permission('admin'):
        return {'crumbs': [{'title': 'Administration',
                            'url': request.route_url('admin')},
                           {'title': 'Content',
                            'url': request.current_route_url(),
                            'current': True}]}
    else:
        raise unauthorised_redirect(request)


@view_config(route_name='admin.content.regenerate')
@current_user()
@require_logged_in()
def content_regenerate(request):
    if request.current_user.has_permission('admin'):
        dbsession = DBSession()
        with transaction.manager:
            for part in dbsession.query(Part):
                if part.content:
                    part.compiled_content = compile_rst(part.content, request, part)
        request.session.flash('The content of all parts has been regenerated',
                              queue='info')
        raise HTTPSeeOther(request.route_url('admin.content'))
    else:
        raise unauthorised_redirect(request)
