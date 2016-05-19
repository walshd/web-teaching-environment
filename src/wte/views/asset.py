# -*- coding: utf-8 -*-
"""
################################
:mod:`wte.views.asset` -- Assets
################################

The :mod:`~wte.views.asset` module provides the backend functionality for
creating, editing, and deleting :class:`~wte.models.Asset`.

Routes are defined in :func:`~wte.views.asset.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import formencode
import hashlib
import transaction

from mimetypes import guess_type
from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound, HTTPNotModified)
from pywebtools.pyramid.auth.views import current_user
from pyramid.response import Response
from pyramid.view import view_config
from pywebtools.formencode import State, CSRFSchema
from pywebtools.sqlalchemy import DBSession
from sqlalchemy import and_

from wte.decorators import (require_logged_in)
from wte.models import (Part, Asset)
from wte.views.part import (create_part_crumbs, get_user_part_progress)
from wte.util import (unauthorised_redirect)


def init(config):
    """Adds the asset-specific routes (route name, URL pattern
    handler):

    * ``asset.new`` -- ``/parts/{pid}/assets/new/{new_type}`` --
      :func:`~wte.views.asset.new`
    * ``asset.search`` -- ``/parts/{pid}/assets/search`` --
      :func:`~wte.views.asset.search`
    * ``asset.edit`` -- ``/parts/{pid}/assets/{aid}/edit`` --
      :func:`~wte.views.asset.edit`
    * ``asset.delete`` -- ``/parts/{pid}/assets/{aid}/delete`` --
      :func:`~wte.views.asset.delete`
    * ``asset.view`` -- ``/parts/{pid}/files/name/assets/{filename}``
      -- :func:`~wte.views.frontend.view_asset`
    * ``file.view`` -- ``/parts/{pid}/files/name/{filename}``
      -- :func:`~wte.views.frontend.view_file`
    * ``file.save`` -- ``/parts/{pid}/files/id/{fid}/save``
      -- :func:`~wte.views.frontend.save_file`
    """
    config.add_route('asset.new', '/parts/{pid}/assets/new/{new_type}')
    config.add_route('asset.search', '/parts/{pid}/assets/search')
    config.add_route('asset.edit', '/parts/{pid}/assets/{aid}/edit')
    config.add_route('asset.delete', '/parts/{pid}/assets/{aid}/delete')
    config.add_route('asset.view', '/parts/{pid}/files/name/assets/{filename}')
    config.add_route('file.view', '/parts/{pid}/files/name/{filename}')
    config.add_route('file.save', '/parts/{pid}/files/id/{fid}/save')


class NewAssetSchema(CSRFSchema):
    """The :class:`~wte.views.asset.NewAssetSchema` handles the
    validation of a new :class:`~wte.models.Asset`.
    """
    filename = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    """The asset's filename"""
    data = formencode.validators.FieldStorageUploadConverter(not_empty=False, if_missing=None)
    """The asset's data"""


@view_config(route_name='asset.new', renderer='wte:templates/asset/new.kajiki')
@current_user()
@require_logged_in()
def new(request):
    """Handles the ``/parts/{pid}/assets/new/{new_type}`` URL, providing the UI and
    backend for creating a new :class:`~wte.models.Asset`.

    Requires that the user has "edit" rights on the current :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Add %s' % (request.matchdict['new_type'].title()),
                                         'url': request.current_route_url()})
            if request.method == 'POST':
                try:
                    schema = NewAssetSchema()
                    if request.matchdict['new_type'] == 'asset':
                        schema.fields['data'].not_empty = True
                    params = schema.to_python(request.params, State(request=request))
                    if not params['filename'] and params['data'] is None:
                        raise formencode.Invalid('You must specify either a file or filename',
                                                 None,
                                                 None,
                                                 error_dict={'filename': 'You must specify either a file or filename',
                                                             'data': 'You must specify either a file or filename'})
                    dbsession = DBSession()
                    progress = get_user_part_progress(dbsession, request.current_user, part)
                    with transaction.manager:
                        dbsession.add(part)
                        if progress:
                            dbsession.add(progress)
                        mimetype = 'application/binary'
                        if params['filename'] is not None:
                            mimetype = guess_type(params['filename'])
                        if params['data'] is not None:
                            mimetype = guess_type(params['data'].filename)
                            if params['filename'] is None:
                                params['filename'] = params['data'].filename
                        if request.matchdict['new_type'] == 'template':
                            new_order = [a.order for a in part.templates]
                        elif request.matchdict['new_type'] == 'asset':
                            new_order = [a.order for a in part.assets]
                        elif request.matchdict['new_type'] == 'file':
                            new_order = [a.order for a in progress.files] if progress else []
                        new_order.append(0)
                        new_order = max(new_order) + 1
                        new_asset = Asset(filename=params['filename'],
                                          mimetype=mimetype[0] if mimetype[0] else 'application/binary',
                                          type=request.matchdict['new_type'],
                                          order=new_order,
                                          data=params['data'].file.read() if params['data'] is not None else None,
                                          etag=hashlib.sha512(params['data'].file.read()).hexdigest()
                                          if params['data'] is not None else None)
                        dbsession.add(new_asset)
                        part.all_assets.append(new_asset)
                    if request.is_xhr:
                        request.override_renderer = 'json'
                        dbsession.add(new_asset)
                        dbsession.add(part)
                        return {'part': {'id': part.id},
                                'asset': {'id': new_asset.id,
                                          'filename': new_asset.filename}}
                    else:
                        dbsession.add(part)
                        raise HTTPSeeOther(request.route_url('part.view', pid=part.id))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'values': request.params,
                            'part': part,
                            'crumbs': crumbs,
                            'help': ['user', 'teacher', 'asset', 'new.html']}
            return {'part': part,
                    'crumbs': crumbs,
                    'help': ['user', 'teacher', 'asset', 'new.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class EditAssetSchema(CSRFSchema):
    """The :class:`~wte.views.asset.EditAssetSchema` handles the
    validation of updates to an :class:`~wte.models.Asset`.
    """
    filename = formencode.validators.UnicodeString(not_empty=True)
    """The asset's filename"""
    mimetype = formencode.validators.UnicodeString(not_empty=True)
    """The asset's mimetype"""
    mimetype_other = formencode.validators.UnicodeString(not_empty=True)
    """The asset's alternative mimetype"""
    data = formencode.validators.FieldStorageUploadConverter(if_missing=None)
    """The asset's file content"""
    content = formencode.validators.UnicodeString(if_missing=None)
    """The asset's content"""


@view_config(route_name='asset.edit', renderer='wte:templates/asset/edit.kajiki')
@current_user()
@require_logged_in()
def edit(request):
    """Handles the ``/parts/{pid}/assets/{aid}/edit`` URL, providing
    the UI and backend for editing :class:`~wte.models.Asset`.

    Requires that the user has "edit" rights on the current :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    asset = dbsession.query(Asset).join(Part.all_assets).\
        filter(and_(Asset.id == request.matchdict['aid'],
                    Part.id == request.matchdict['pid'])).first()
    if part and asset:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Edit %s' % (asset.type.title()),
                                         'url': request.current_route_url()})
            if request.method == 'POST':
                try:
                    params = EditAssetSchema().to_python(request.params, State(request=request))
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(asset)
                        asset.filename = params['filename']
                        if params['data'] is not None:
                            asset.data = params['data'].file.read()
                            asset.etag = hashlib.sha512(asset.data).hexdigest()
                            mimetype = guess_type(params['data'].filename)
                            if mimetype[0]:
                                mimetype = mimetype[0]
                            else:
                                if params['mimetype'] != 'other':
                                    mimetype = params['mimetype']
                                else:
                                    mimetype = params['mimetype_other']
                        elif params['content'] is not None:
                            asset.data = params['content'].encode('utf-8')
                            asset.etag = hashlib.sha512(asset.data).hexdigest()
                            if params['mimetype'] != 'other':
                                mimetype = params['mimetype']
                            else:
                                mimetype = params['mimetype_other']
                        else:
                            if params['mimetype'] != 'other':
                                mimetype = params['mimetype']
                            else:
                                mimetype = params['mimetype_other']
                        asset.mimetype = mimetype
                    dbsession.add(part)
                    dbsession.add(asset)
                    raise HTTPSeeOther(request.route_url('part.view', pid=part.id))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'values': request.params,
                            'part': part,
                            'asset': asset,
                            'crumbs': crumbs,
                            'help': ['user', 'teacher', 'asset', 'edit.html']}
            return {'part': part,
                    'asset': asset,
                    'crumbs': crumbs,
                    'help': ['user', 'teacher', 'asset', 'edit.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='asset.delete', renderer='wte:templates/asset/delete.kajiki')
@current_user()
@require_logged_in()
def delete(request):
    """Handles the ``/parts/{pid}/assets/{aid}/delete`` URL,
    providing the UI and backend for deleting :class:`~wte.models.Asset`.

    Requires that the user has "edit" rights on the current :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    asset = dbsession.query(Asset).join(Part.all_assets).\
        filter(and_(Asset.id == request.matchdict['aid'],
                    Part.id == request.matchdict['pid'])).first()
    if part and asset:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Delete Asset',
                                         'url': request.current_route_url()})
            if request.method == 'POST':
                try:
                    CSRFSchema().to_python(request.params, State(request=request))
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(asset)
                        asset.parts = []
                        dbsession.delete(asset)
                    dbsession.add(part)
                    raise HTTPSeeOther(request.route_url('part.view', pid=part.id))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'part': part,
                            'asset': asset,
                            'crumbs': crumbs,
                            'help': ['user', 'teacher', 'asset', 'delete.html']}
            return {'part': part,
                    'asset': asset,
                    'crumbs': crumbs,
                    'help': ['user', 'teacher', 'asset', 'delete.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='file.view')
@current_user()
@require_logged_in()
def view_file(request):
    """Handles the ``parts/{ptid}/pages/{pid}/users/{uid}/files/name/{filename}``
    URL, sending back the correct :class:`~wte.models.Asset`.

    Requires that the user has "view" rights on the :class:`~wte.models.Part`.
    It will also only send an :class:`~wte.models.Asset` belonging to the current
    :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            progress = get_user_part_progress(dbsession, request.current_user, part)
            for user_file in progress.files:
                if user_file.filename == request.matchdict['filename']:
                    if 'If-None-Match' in request.headers and request.headers['If-None-Match'] == user_file.etag:
                        raise HTTPNotModified()
                    headers = [('Content-Type', str(user_file.mimetype))]
                    if user_file.etag is not None:
                        headers.append(('ETag', str(user_file.etag)))
                    if 'download' in request.params:
                        headers.append(('Content-Disposition',
                                        str('attachment; filename="%s"' % (user_file.filename))))
                    return Response(body=user_file.data,
                                    headerlist=headers)
            raise HTTPNotFound()
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='file.save', renderer='json')
@current_user()
@require_logged_in()
def save_file(request):
    """Handles the ``/parts/{pid}/files/id/{fid}/save``
    URL, updating the :class:`~wte.models.Asset`'s content.

    Requires that the user has "view" rights on the :class:`~wte.models.Part`.
    It will also only update an :class:`~wte.models.Asset` belonging to the
    current :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            progress = get_user_part_progress(dbsession, request.current_user, part)
            for user_file in progress.files:
                if user_file.id == int(request.matchdict['fid']):
                    if 'content' in request.params:
                        with transaction.manager:
                            dbsession.add(user_file)
                            user_file.data = request.params['content'].encode('utf-8')
                            user_file.etag = hashlib.sha512(user_file.data).hexdigest()
                        return {'status': 'saved'}
                    else:
                        return {'status': 'no-changes'}
            raise HTTPNotFound()
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='asset.view')
@current_user()
@require_logged_in()
def view_asset(request):
    """Handles the ``/parts/{pid}/files/name/assets/{filename}``
    URL, sending back the correct :class:`~wte.models.Asset`.

    Requires that the user has "view" rights on the :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part.type == 'page':
        part = part.parent
    asset = dbsession.query(Asset).join(Part.assets).\
        filter(and_(Asset.filename == request.matchdict['filename'],
                    Part.id == part.id)).first()
    if part and asset:
        if part.allow('view', request.current_user):
            if 'If-None-Match' in request.headers and request.headers['If-None-Match'] == asset.etag:
                raise HTTPNotModified()
            headerlist = [('Content-Type', str(asset.mimetype))]
            if asset.etag is not None:
                headerlist.append(('ETag', str(asset.etag)))
            if 'download' in request.params:
                if request.params['download'].lower() == 'true':
                    headerlist.append(('Content-Disposition', str('attachment; filename="%s"' % (asset.filename))))
            return Response(body=asset.data,
                            headerlist=headerlist)
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='asset.search', renderer='json')
@current_user()
@require_logged_in()
def search(request):
    """Handles the ``/parts/{pid}/assets/search`` URL, searching
    for all :class:`~wte.models.Asset` that have a filename that
    matches the 'q' request parameter and that belong to either the
    current :class:`~wte.models.Part` or any of its ancestors.
    The current user must have the "view" permission on the current
    :class:`~wte.models.Part` to see any results.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            assets = []
            if 'q' in request.params:
                while part is not None:
                    assets.extend([asset for asset in part.assets if request.params['q'] in asset.filename])
                    part = part.parent
            return [{'id': asset.filename, 'value': asset.filename} for asset in assets]
        else:
            raise unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
