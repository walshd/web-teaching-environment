# -*- coding: utf-8 -*-
u"""
#######################################
:mod:`wte.views.asset` -- Asset Backend
#######################################

The :mod:`~wte.views.asset` module provides the backend functionality for
creating, editing, and deleting :class:`~wte.models.Asset`.

Routes are defined in :func:`~wte.views.asset.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import transaction
import formencode

from mimetypes import guess_type
from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound, HTTPForbidden)
from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools.auth import is_authorised
from sqlalchemy import and_

from wte.decorators import current_user
from wte.models import (DBSession, Module, Part, Asset)
from wte.text_formatter import compile_rst
from wte.views.part import create_part_crumbs
from wte.util import (unauthorised_redirect)


def init(config):
    u"""Adds the asset-specific backend routes (route name, URL pattern
    handler):
    
    * ``asset.new`` -- ``/modules/{mid}/parts/{pid}/assets/new`` --
      :func:`~wte.views.asset.new`
    * ``asset.edit`` -- ``/modules/{mid}/parts/{pid}/assets/{aid}/edit`` --
      :func:`~wte.views.asset.edit`
    * ``asset.delete`` -- ``/modules/{mid}parts/{pid}/assets/{aid}/delete`` --
      :func:`~wte.views.asset.delete`
    """
    config.add_route('asset.new', '/modules/{mid}/parts/{pid}/assets/new')
    config.add_route('asset.edit', '/modules/{mid}/parts/{pid}/assets/{aid}/edit')
    config.add_route('asset.delete', '/modules/{mid}/parts/{pid}/assets/{aid}/delete')


class NewAssetSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.NewAssetSchema` handles the
    validation of a new :class:`~wte.models.Asset`.
    """
    filename = formencode.validators.UnicodeString(not_empty=True)
    u"""The asset's filename"""
    content = formencode.validators.FieldStorageUploadConverter(not_empty=True)
    u"""The asset's data"""


@view_config(route_name='asset.new')
@render({'text/html': 'asset/new.html'})
@current_user()
def new(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/assets/new`` URL, providing the UI and
    backend for creating a new :class:`~wte.models.Part`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    part = dbsession.query(Part).filter(Part.id==request.matchdict[u'pid']).first()
    if module:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if part:
                if part.type == u'tutorial':
                    available_types = [('page', 'Page')]
                elif part.type == u'exercise':
                    available_types = [('task', 'Task')]
                else:
                    available_types = []
            else:
                available_types = [('tutorial', 'Tutorial'), ('exercise', 'Exercise')]
            crumbs = create_part_crumbs(request,
                                        module,
                                        part,
                                        {'title': 'Add Asset',
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                try:
                    params = NewAssetSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(part)
                        mimetype = guess_type(params['content'].filename)
                        dbsession.add(Asset(part_id=part.id,
                                            filename=params['filename'],
                                            mimetype=mimetype[0] if mimetype[0] else 'application/binary',
                                            data=params['content'].file.read()))
                    dbsession.add(part)
                    request.session.flash('Your new asset has been created', queue='info')
                    raise HTTPSeeOther(request.route_url('part.view', mid=request.matchdict['mid'], pid=part.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'part': part,
                            'available_types': available_types,
                            'crumbs': crumbs}
            return {'module': module,
                    'part': part,
                    'available_types': available_types,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class EditAssetSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.EditAssetSchema` handles the
    validation of updates to an :class:`~wte.models.Asset`.
    """
    filename = formencode.validators.UnicodeString(not_empty=True)
    u"""The asset's filename"""
    mimetype = formencode.validators.UnicodeString(not_empty=True)
    u"""The asset's mimetype"""
    content = formencode.validators.FieldStorageUploadConverter()
    u"""The asset's content"""
    

@view_config(route_name='asset.edit')
@render({'text/html': 'asset/edit.html'})
@current_user()
def edit(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/assets/new`` URL, providing
    the UI and backend for creating a new :class:`~wte.models.Asset`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    part = dbsession.query(Part).filter(Part.id==request.matchdict[u'pid']).first()
    asset = dbsession.query(Asset).filter(and_(Asset.id==request.matchdict[u'aid'],
                                              Asset.part_id==part.id)).first()
    if module and part and asset:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            crumbs = create_part_crumbs(request,
                                        module,
                                        part,
                                        {'title': 'Edit Asset',
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                try:
                    params = EditAssetSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(asset)
                        asset.filename = params['filename']
                        print params['content']
                        if params['content'] is not None:
                            asset.data = params['content'].file.read()
                            mimetype = guess_type(params['content'].filename)
                            if mimetype[0]:
                                mimetype = mimetype[0]
                            else:
                                mimetype = params['mimetype']
                        else:
                            mimetype = params['mimetype']
                        asset.mimetype = mimetype
                    dbsession.add(part)
                    request.session.flash('Your asset has been updated', queue='info')
                    raise HTTPSeeOther(request.route_url('part.view', mid=request.matchdict['mid'], pid=part.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'part': part,
                            'asset': asset,
                            'crumbs': crumbs}
            return {'module': module,
                    'part': part,
                    'asset': asset,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='asset.delete')
@render({'text/html': 'asset/delete.html'})
@current_user()
def delete(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/assets/{aid}/delete`` URL,
    providing the UI and backend for creating a new :class:`~wte.models.Asset`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    part = dbsession.query(Part).filter(Part.id==request.matchdict[u'pid']).first()
    asset = dbsession.query(Asset).filter(and_(Asset.id==request.matchdict[u'aid'],
                                              Asset.part_id==part.id)).first()
    if module and part and asset:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            crumbs = create_part_crumbs(request,
                                        module,
                                        part,
                                        {'title': 'Delete Asset',
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                try:
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.delete(asset)
                    dbsession.add(part)
                    request.session.flash('Your asset has been deleted', queue='info')
                    raise HTTPSeeOther(request.route_url('part.view', mid=request.matchdict['mid'], pid=part.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'part': part,
                            'asset': asset,
                            'crumbs': crumbs}
            return {'module': module,
                    'part': part,
                    'asset': asset,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
