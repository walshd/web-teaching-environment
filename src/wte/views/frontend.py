# -*- coding: utf-8 -*-
u"""
###################################################
:mod:`wte.views.frontend` -- Frontend view handlers
###################################################

The :mod:`~wte.views.frontend` handles the frontend functionality for
interacting with :class:`~wte.models.Module`, :class:`~wte.models.Part`, and
:class:`~wte.models.Page`.

Routes are defined in :func:`~wte.views.frontend.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import hashlib
import transaction

from pyramid.httpexceptions import (HTTPNotFound, HTTPSeeOther, HTTPNotModified)
from pyramid.response import Response
from pyramid.view import view_config
from pywebtools.renderer import render
from sqlalchemy import and_
from StringIO import StringIO
from zipfile import ZipFile

from wte.decorators import (current_user, require_logged_in)
from wte.models import (DBSession, Part, UserPartProgress, Asset)
from wte.util import (unauthorised_redirect)
from wte.views.part import (create_part_crumbs, get_user_part_progress)


def init(config):
    u"""Adds the frontend-specific routes (route name, URL pattern
    handler):

    * ``asset.view`` -- ``/parts/{pid}/files/name/assets/{filename}``
      -- :func:`~wte.views.frontend.view_asset`
    * ``file.view`` -- ``/parts/{pid}/files/name/{filename}``
      -- :func:`~wte.views.frontend.view_file`
    * ``file.save`` -- ``/parts/{pid}/files/id/{fid}/save``
      -- :func:`~wte.views.frontend.save_file`
    """
    config.add_route('asset.view', '/parts/{pid}/files/name/assets/{filename}')
    config.add_route('file.view', '/parts/{pid}/files/name/{filename}')
    config.add_route('file.save', '/parts/{pid}/files/id/{fid}/save')


@view_config(route_name='file.view')
@current_user()
@require_logged_in()
def view_file(request):
    u"""Handles the ``parts/{ptid}/pages/{pid}/users/{uid}/files/name/{filename}``
    URL, sending back the correct :class:`~wte.models.Asset`.

    Requires that the user has "view" rights on the :class:`~wte.models.Part`.
    It will also only send an :class:`~wte.models.Asset` belonging to the current
    :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict[u'pid']).first()
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


@view_config(route_name='file.save')
@render({'application/json': True})
@current_user()
@require_logged_in()
def save_file(request):
    u"""Handles the ``/parts/{pid}/files/id/{fid}/save``
    URL, updating the :class:`~wte.models.Asset`'s content.

    Requires that the user has "view" rights on the :class:`~wte.models.Part`.
    It will also only update an :class:`~wte.models.Asset` belonging to the
    current :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict[u'pid']).first()
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
    u"""Handles the ``/parts/{pid}/files/name/assets/{filename}``
    URL, sending back the correct :class:`~wte.models.Asset`.

    Requires that the user has "view" rights on the :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict[u'pid']).first()
    if part.type == u'page':
        part = part.parent
    asset = dbsession.query(Asset).join(Part.assets).\
        filter(and_(Asset.filename == request.matchdict[u'filename'],
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
