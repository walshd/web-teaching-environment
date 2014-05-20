# -*- coding: utf-8 -*-
u"""
###################################################
:mod:`wte.views.frontend` -- Frontend view handlers
###################################################

The :mod:`~wte.views.frontend` handles all routes related to the user working
through a :mod:`~wte.models.Tutorial`.

Routes are defined in :func:`~wte.views.frontend.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from pyramid.view import view_config
from pywebtools.auth import is_authorised
from pywebtools.renderer import render
from sqlalchemy import and_

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from wte.decorators import current_user
from wte.models import (DBSession, Module, Tutorial, Page, User)
from wte.util import (unauthorised_redirect, State, send_email, get_config_setting)

def init(config):
    u"""Adds the frontend-specific backend routes (route name, URL pattern
    handler):
    
    * ``modules`` -- ``/modules`` -- :func:`~wte.views.frontend.modules`
    * ``module.view`` -- ``/modules/{mid}`` --
      :func:`~wte.views.frontend.view_module`
    * ``tutorial.view`` -- ``/modules/{mid}/tutorials/{tid}`` --
      :func:`~wte.views.frontend.view_tutorial`
    * ``page.view`` -- ``/modules/{mid}/tutorials/{tid}/pages/{pid}`` --
      :func:`~wte.views.frontend.view_page`
    * ``user.modules`` -- ``/users/{uid}/modules`` --
      :func:`~wte.views.frontend.user_modules`
    """
    config.add_route('modules', '/modules')
    config.add_route('module.view', '/modules/{mid}')
    config.add_route('tutorial.view', '/modules/{mid}/tutorials/{tid}')
    config.add_route('page.view', '/modules/{mid}/tutorials/{tid}/pages/{pid}')
    config.add_route('user.modules', '/users/{uid}/modules')

@view_config(route_name='modules')
@render({'text/html': 'module/list.html'})
@current_user()
def modules(request):
    u"""Handles the ``/modules`` URL, displaying all available
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    modules = dbsession.query(Module).filter(Module.status==u'available').all()
    return {'modules': modules,
            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules'), 'current': True}]}

@view_config(route_name='user.modules')
@render({'text/html': 'module/user.html'})
@current_user()
def user_modules(request):
    u"""Handles the ``/users/{uid}/modules`` URL, displaying all the
    :class:`~wte.models.Module` of the :class:`~wte.models.User`.
    
    Requires that the current user has "view" rights for the
    :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id==request.matchdict['uid']).first()
    if user:
        if user.allow('view', request.current_user):
            taught_modules = dbsession.query(Module).filter(Module.owner_id==request.matchdict['uid']).order_by(Module.title).all()
            return {'user': user,
                    'taught_modules': taught_modules,
                    'crumbs': [{'title': user.display_name, 'url': request.route_url('user.view', uid=user.id)},
                               {'title': 'Modules', 'url': request.route_url('modules'), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
    
@view_config(route_name='module.view')
@render({'text/html': 'module/view.html'})
@current_user()
def view_module(request):
    u"""Handles the ``/modules/{mid}`` URL, displaying the
    :class:`~wte.models.Module` and its child :class:`~wte.models.Tutorial`.
    
    Requires that the user has "view" rights on the
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    if module:
        if is_authorised(u':module.allow("view" :current)', {'module': module,
                                                             'current': request.current_user}):
            return {'module': module,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='tutorial.view')
@render({'text/html': 'tutorial/view.html'})
@current_user()
def view_tutorial(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}`` URL, displaying the
    :class:`~wte.models.Tutorial` and its child :class:`~wte.models.Page`.
    
    Requires that the user has "view" rights on the
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    tutorial = dbsession.query(Tutorial).filter(and_(Tutorial.id==request.matchdict['tid'],
                                                     Tutorial.module_id==request.matchdict['mid'])).first()
    if module and tutorial:
        if is_authorised(u':module.allow("view" :current)', {'module': module,
                                                             'current': request.current_user}):
            return {'module': module,
                    'tutorial': tutorial,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='page.view')
@render({'text/html': 'page/view.html'})
@current_user()
def view_page(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/pages/{pid}`` URL,
    displaying the :class:`~wte.models.Page`.
    
    Requires that the user has "view" rights on the
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict[u'mid']).first()
    tutorial = dbsession.query(Tutorial).filter(and_(Tutorial.id==request.matchdict[u'tid'],
                                                     Tutorial.module_id==request.matchdict[u'mid'])).first()
    page = dbsession.query(Page).filter(and_(Page.id==request.matchdict[u'pid'],
                                             Page.tutorial_id==request.matchdict[u'tid'])).first()
    if module and tutorial and page:
        if is_authorised(u':module.allow("view" :current)', {'module': module,
                                                             'current': request.current_user}):
            prev_page = None
            next_page = None
            page_no = 1
            state = 0
            for p in tutorial.pages:
                if p == page:
                    state = 1
                else:
                    if state == 0:
                        page_no = page_no + 1
                        prev_page = p
                    elif state == 1:
                        state = 2
                        next_page = p
            return {'module': module,
                    'tutorial': tutorial,
                    'page': page,
                    'prev_page': prev_page,
                    'next_page': next_page,
                    'page_no': page_no,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id), 'current': True}]
                    }
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
