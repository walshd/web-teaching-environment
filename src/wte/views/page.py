# -*- coding: utf-8 -*-
u"""
#####################################
:mod:`wte.views.page` -- Page Backend
#####################################

The :mod:`~wte.views.page` module provides the backend functionality for
creating, editing, and deleting :class:`~wte.models.Page`. It also provides
functionality to preview ReST text.

Routes are defined in :func:`~wte.views.page.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import transaction
import formencode

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound, HTTPForbidden)
from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools.auth import is_authorised
from sqlalchemy import and_

from wte.decorators import current_user
from wte.util import (unauthorised_redirect)
from wte.models import (DBSession, Module, Part, Page)
from wte.text_formatter import compile_rst

def init(config):
    u"""Adds the page-specific backend routes (route name, URL pattern
    handler):
    
    * ``page.new`` -- ``/modules/{mid}/tutorials/{tid}/pages/new`` --
      :func:`~wte.views.tutorial.new`
    * ``page.edit`` -- ``/modules/{mid}/tutorials/{tid}/pages/{pid}/edit`` --
      :func:`~wte.views.tutorial.edit`
    * ``page.delete`` -- ``/modules/{mid}/tutorials/{tid}/pages/{pid}/delete``
      -- :func:`~wte.views.tutorial.delete`
    * ``page.edit`` -- ``/modules/{mid}/tutorials/{tid}/pages/{pid}/preview``
      -- :func:`~wte.views.tutorial.preview`
    """
    config.add_route('page.new', '/modules/{mid}/tutorials/{tid}/pages/new')
    config.add_route('page.edit', '/modules/{mid}/tutorials/{tid}/pages/{pid}/edit')
    config.add_route('page.delete', '/modules/{mid}/tutorials/{tid}/pages/{pid}/delete')
    config.add_route('page.preview', '/modules/{mid}/tutorials/{tid}/pages/{pid}/preview')

class PageSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.PageSchema` handles the validation
    of a new or updated :class:`~wte.models.Page`.
    """
    title = formencode.validators.UnicodeString(not_empty=True)
    u"""The page's title"""
    content = formencode.validators.UnicodeString(if_missing=u'')
    u"""The page's ReST content"""
    
@view_config(route_name='page.new')
@render({'text/html': 'page/new.html'})
@current_user()
def new(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/pages/new`` URL,
    providing the UI and backend for creating a new
    :class:`~wte.models.Page`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    if module and tutorial:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                try:
                    params = PageSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(tutorial)
                        max_order = [t.order + 1 for t in tutorial.pages]
                        max_order.append(0)
                        max_order = max(max_order)
                        
                        new_page = Page(title=params['title'],
                                        part=tutorial,
                                        content=u'',
                                        order=max_order)
                        dbsession.add(new_page)
                    dbsession.add(new_page)
                    request.session.flash('Your new page has been created', queue='info')
                    raise HTTPSeeOther(request.route_url('page.edit', mid=request.matchdict['mid'], tid=request.matchdict['tid'], pid=new_page.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'tutorial': tutorial,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                                       {'title': 'Add page', 'url': request.route_url('page.new', mid=module.id, tid=tutorial.id), 'current': True}]}
            return {'module': module,
                    'tutorial': tutorial,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                               {'title': 'Add page', 'url': request.route_url('page.new', mid=module.id, tid=tutorial.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='page.edit')
@render({'text/html': 'page/edit.html'})
@current_user()
def edit(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/pages/{pid}/edit`` URL,
    providing the UI and backend for editing a :class:`~wte.models.Page`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    page = dbsession.query(Page).filter(and_(Page.id==request.matchdict['pid'],
                                             Page.part_id==request.matchdict['tid'])).first()
    if module and tutorial and page:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                try:
                    params = PageSchema().to_python(request.params)
                    with transaction.manager:
                        dbsession.add(page)
                        page.title = params['title']
                        page.content = params['content']
                    request.session.flash('The page has been updated', queue='info')
                    raise HTTPSeeOther(request.route_url('page.view', mid=request.matchdict['mid'], tid=request.matchdict['tid'], pid=request.matchdict['pid']))
                except formencode.Invalid as e:
                    e.params = params
                    return {'e': e,
                            'module': module,
                            'tutorial': tutorial,
                            'page': page,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                                       {'title': page.title, 'url': request.route_url('page.view', mid=module.id, tid=tutorial.id, pid=page.id)},
                                       {'title': 'Edit', 'url': request.route_url('page.edit', mid=module.id, tid=tutorial.id, pid=page.id), 'current': True}]}
            return {'module': module,
                    'tutorial': tutorial,
                    'page': page,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                               {'title': page.title, 'url': request.route_url('page.view', mid=module.id, tid=tutorial.id, pid=page.id)},
                               {'title': 'Edit', 'url': request.route_url('page.edit', mid=module.id, tid=tutorial.id, pid=page.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='page.delete')
@render({'text/html': 'page/delete.html'})
@current_user()
def delete(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/pages/{pid}/delete`` URL,
    providing the UI and backend for deleting a :class:`~wte.models.Page`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    page = dbsession.query(Page).filter(and_(Page.id==request.matchdict['pid'],
                                             Page.part_id==request.matchdict['tid'])).first()
    if module and tutorial and page:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                with transaction.manager:
                    dbsession.delete(page)
                request.session.flash('The page has been deleted', queue='info')
                raise HTTPSeeOther(request.route_url('tutorial.view', mid=request.matchdict['mid'], tid=request.matchdict['tid']))
            return {'module': module,
                    'tutorial': tutorial,
                    'page': page,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                               {'title': page.title, 'url': request.route_url('page.view', mid=module.id, tid=tutorial.id, pid=page.id)},
                               {'title': 'Delete', 'url': request.route_url('page.delete', mid=module.id, tid=tutorial.id, pid=page.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
            
@view_config(route_name='page.preview')
@render({'application/json': True})
@current_user()
def preview(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/pages/{pid}/preview`` URL,
    generating an HTML preview of the submitted ReST. The ReST text to render
    has to be set as the ``content`` parameter.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    page = dbsession.query(Page).filter(and_(Page.id==request.matchdict['pid'],
                                             Page.part_id==request.matchdict['tid'])).first()
    if module and tutorial and page:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if 'content' in request.params:
                return {'content': compile_rst(request.params['content'])}
        else:
            raise HTTPForbidden()
    else:
        raise HTTPNotFound()
    