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
from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from pyramid.view import view_config
from pywebtools import text
from pywebtools.renderer import render
from sqlalchemy import and_

from wte.decorators import current_user
from wte.models import (DBSession, Part, Asset)
from wte.views.part import create_part_crumbs
from wte.util import (unauthorised_redirect)


def init(config):
    u"""Adds the asset-specific backend routes (route name, URL pattern
    handler):

    * ``asset.new`` -- ``/parts/{pid}/assets/new/{new_type}`` --
      :func:`~wte.views.asset.new`
    * ``asset.edit`` -- ``/parts/{pid}/assets/{aid}/edit`` --
      :func:`~wte.views.asset.edit`
    * ``asset.delete`` -- ``/parts/{pid}/assets/{aid}/delete`` --
      :func:`~wte.views.asset.delete`
    """
    config.add_route('asset.new', '/parts/{pid}/assets/new/{new_type}')
    config.add_route('asset.edit', '/parts/{pid}/assets/{aid}/edit')
    config.add_route('asset.delete', '/parts/{pid}/assets/{aid}/delete')


class NewAssetSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.NewAssetSchema` handles the
    validation of a new :class:`~wte.models.Asset`.
    """
    filename = formencode.validators.UnicodeString(not_empty=True)
    u"""The asset's filename"""
    data = formencode.validators.FieldStorageUploadConverter()
    u"""The asset's data"""


@view_config(route_name='asset.new')
@render({'text/html': 'asset/new.html'})
@current_user()
def new(request):
    u"""Handles the ``/parts/{pid}/assets/new/{new_type}`` URL, providing the UI and
    backend for creating a new :class:`~wte.models.Asset`.

    Requires that the user has "edit" rights on the current :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict[u'pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Add %s' % (text.title(request.matchdict['new_type'])),
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                try:
                    params = NewAssetSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(part)
                        mimetype = guess_type(params['filename'])
                        if params['data'] is not None:
                            mimetype = guess_type(params['data'].filename)
                        if request.matchdict['new_type'] == 'template':
                            new_order = [a.order for a in part.templates]
                        elif request.matchdict['new_type'] == 'asset':
                            new_order = [a.order for a in part.assets]
                        new_order.append(0)
                        new_order = max(new_order) + 1
                        new_asset = Asset(filename=params['filename'],
                                          mimetype=mimetype[0] if mimetype[0] else 'application/binary',
                                          type=request.matchdict['new_type'],
                                          order=new_order,
                                          data=params['data'].file.read() if params['data'] is not None else None)
                        dbsession.add(new_asset)
                        if request.matchdict['new_type'] == 'template':
                            part.templates.append(new_asset)
                        elif request.matchdict['new_type'] == 'asset':
                            part.assets.append(new_asset)
                    dbsession.add(part)
                    request.session.flash('Your new %s has been created' % (request.matchdict['new_type']),
                                          queue='info')
                    raise HTTPSeeOther(request.route_url('part.view', pid=part.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'part': part,
                            'crumbs': crumbs}
            return {'part': part,
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
    mimetype_other = formencode.validators.UnicodeString(not_empty=True)
    u"""The asset's alternative mimetype"""
    data = formencode.validators.FieldStorageUploadConverter(if_missing=None)
    u"""The asset's file content"""
    content = formencode.validators.UnicodeString(if_missing=None)
    u"""The asset's content"""


@view_config(route_name='asset.edit')
@render({'text/html': 'asset/edit.html'})
@current_user()
def edit(request):
    u"""Handles the ``/parts/{pid}/assets/{aid}/edit`` URL, providing
    the UI and backend for editing :class:`~wte.models.Asset`.

    Requires that the user has "edit" rights on the current :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict[u'pid']).first()
    asset = dbsession.query(Asset).join(Part.assets).\
        filter(and_(Asset.id == request.matchdict[u'aid'],
                    Part.id == request.matchdict[u'pid'])).first()
    if part and asset:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Edit %s' % (text.title(asset.type)),
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                try:
                    params = EditAssetSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(asset)
                        asset.filename = params['filename']
                        if params['data'] is not None:
                            asset.data = params['data'].file.read()
                            mimetype = guess_type(params['content'].filename)
                            if mimetype[0]:
                                mimetype = mimetype[0]
                            else:
                                mimetype = params['mimetype']
                        if params['content'] is not None:
                            asset.data = params['content'].encode('utf-8')
                            mimetype = params['mimetype']
                        else:
                            mimetype = params['mimetype']
                        asset.mimetype = mimetype
                    dbsession.add(part)
                    dbsession.add(asset)
                    request.session.flash('Your %s has been updated' % (asset.type), queue='info')
                    raise HTTPSeeOther(request.route_url('part.view', pid=part.id))
                except formencode.Invalid as e:
                    print e
                    e.params = request.params
                    return {'e': e,
                            'part': part,
                            'asset': asset,
                            'crumbs': crumbs}
            return {'part': part,
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
    u"""Handles the ``/parts/{pid}/assets/{aid}/delete`` URL,
    providing the UI and backend for deleting :class:`~wte.models.Asset`.

    Requires that the user has "edit" rights on the current :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict[u'pid']).first()
    asset = dbsession.query(Asset).join(Part.assets).\
        filter(and_(Asset.id == request.matchdict[u'aid'],
                    Part.id == request.matchdict[u'pid'])).first()
    if part and asset:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Delete Asset',
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                try:
                    dbsession = DBSession()
                    asset_type = asset.type
                    with transaction.manager:
                        dbsession.add(asset)
                        asset.parts = []
                        dbsession.delete(asset)
                    dbsession.add(part)
                    request.session.flash('Your %s has been deleted' % (asset_type), queue='info')
                    raise HTTPSeeOther(request.route_url('part.view', pid=part.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'part': part,
                            'asset': asset,
                            'crumbs': crumbs}
            return {'part': part,
                    'asset': asset,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
