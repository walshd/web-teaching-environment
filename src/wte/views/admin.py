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
from pywebtools.pyramid.auth.decorators import unauthorised_redirect, require_logged_in
from pywebtools.pyramid.auth.views import current_user
from pywebtools.pyramid.util import paginate
from pywebtools.sqlalchemy import DBSession

from wte.models import (Part)
from wte.text_formatter import compile_rst


def init(config):
    """Adds the admin-specific routes (route name, URL pattern
    handler):

    * ``admin`` -- ``/admin`` -- :func:`~wte.views.admin.admin`
    * ``admin.content`` -- ``/admin/content`` --
      :func:`~wte.views.admin.content_admin`
    * ``admin.content.regenerate`` -- ``/admin/content/regenerate``
      -- :func:`~wte.views.admin.content_regenerate`
    * ``admin.content.list`` -- ``/admin/content/list``
      -- :func:`~wte.views.admin.content_list`
    """
    config.add_route('admin', '/admin')
    config.add_route('admin.content', '/admin/content')
    config.add_route('admin.content.list', '/admin/content/list')
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


@view_config(route_name='admin.content', renderer="wte:templates/admin/content/index.kajiki")
@current_user()
@require_logged_in()
def content_admin(request):
    """Handles the ``/admin/content`` URL, displaying all available administrative
    functions related to the content administrations.
    """
    if request.current_user.has_permission('admin.modules.view'):
        return {'crumbs': [{'title': 'Administration',
                            'url': request.route_url('admin')},
                           {'title': 'Content',
                            'url': request.current_route_url(),
                            'current': True}]}
    else:
        raise unauthorised_redirect(request)


@view_config(route_name='admin.content.list', renderer="wte:templates/admin/content/list.kajiki")
@current_user()
@require_logged_in()
def content_list(request):
    """Handles the ``/admin/content/list`` URL providing administrative access
    to all :class:`~wte.models.Part`\ s.
    """
    if request.current_user.has_permission('admin.modules.view'):
        dbsession = DBSession()
        modules = dbsession.query(Part).filter(Part.parent_id == None)
        try:
            start = int(request.params['start'])
        except:
            start = 0
        if 'q' in request.params and request.params['q']:
            modules = modules.filter(Part.title.contains(request.params['q']))
        if 'status' in request.params and request.params['status']:
            modules = modules.filter(Part.status == request.params['status'])
        pages = paginate(request, 'admin.content.list', modules, start, 25)
        modules = modules.offset(start).limit(25)
        return {'modules': modules,
                'pages': pages,
                'crumbs': [{'title': 'Administration',
                            'url': request.route_url('admin')},
                           {'title': 'Content',
                            'url': request.route_url('admin.content')},
                           {'title': 'All Modules',
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
    if request.current_user.has_permission('admin.modules.edit'):
        if request.method == 'POST':
            dbsession = DBSession()
            with transaction.manager:
                for part in dbsession.query(Part):
                    if part.content:
                        part.compiled_content = compile_rst(part.content, request, part)
            request.session.flash('Regeneration complete', queue='info')
        raise HTTPSeeOther(request.route_url('admin.content'))
    else:
        raise unauthorised_redirect(request)
