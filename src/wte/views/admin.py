# -*- coding: utf-8 -*-
"""
#############################################
:mod:`wte.views.admin` -- Admin view handlers
#############################################

The :mod:`~wte.views.admin` handles the requests relating to general
administrative functionality.

Routes are defined in :func:`~wte.views.admin.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import transaction

from pyramid.httpexceptions import HTTPSeeOther
from pyramid.view import view_config
from pywebtools.pyramid.auth import current_user
from pywebtools.sqlalchemy import DBSession

from wte.decorators import (require_logged_in)
from wte.models import (Part)
from wte.text_formatter import compile_rst
from wte.util import unauthorised_redirect


def init(config):
    """Adds the admin-specific routes (route name, URL pattern
    handler):

    * ``admin`` -- ``/admin`` -- :func:`~wte.views.admin.admin`
    * ``admin.content`` -- ``/admin/content`` --
      :func:`~wte.views.admin.content_admin`
    * ``admin.content.regenerate`` -- ``/admin/content/regenerate``
      -- :func:`~wte.views.admin.content_regenerate`
    """
    config.add_route('admin', '/admin')
    config.add_route('admin.content', '/admin/content')
    config.add_route('admin.content.regenerate', '/admin/content/regenerate')


@view_config(route_name='admin', renderer='wte:templates/admin/index.kajiki')
@current_user()
@require_logged_in()
def admin(request):
    """Handles the ``/admin`` URL, displaying all available administrative
    functions.
    """
    if request.current_user.has_permission('admin'):
        return {'crumbs': [{'title': 'Administration',
                            'url': request.current_route_url(),
                            'current': True}]}
    else:
        raise unauthorised_redirect(request)


@view_config(route_name='admin.content', renderer="wte:templates/admin/content.kajiki")
@current_user()
@require_logged_in()
def content_admin(request):
    """Handles the ``/admin/content`` URL, displaying all available administrative
    functions related to the content administrations.
    """
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
    """Handles the ``/admin/content/regenerate`` URL, regenerating the
    ``compiled_content`` attribute for all :class:`~wte.models.Part`\ s.
    """
    if request.current_user.has_permission('admin'):
        if request.method == 'POST':
            dbsession = DBSession()
            with transaction.manager:
                for part in dbsession.query(Part):
                    if part.content:
                        part.compiled_content = compile_rst(part.content, request, part)
            request.session.flash('All contents have been regenerated.', queue='info')
        raise HTTPSeeOther(request.route_url('admin.content'))
    else:
        raise unauthorised_redirect(request)
