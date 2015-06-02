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
import transaction

from pyramid.httpexceptions import (HTTPNotFound, HTTPSeeOther)
from pyramid.response import Response
from pyramid.view import view_config
from pywebtools.renderer import render
from sqlalchemy import and_
from StringIO import StringIO
from zipfile import ZipFile

from wte.decorators import (current_user, require_logged_in)
from wte.models import (DBSession, Part, User, UserPartProgress,
                        Asset, UserPartRole)
from wte.util import (unauthorised_redirect)
from wte.views.part import (create_part_crumbs, get_user_part_progress)


def init(config):
    u"""Adds the frontend-specific routes (route name, URL pattern
    handler):

    * ``modules`` -- ``/modules`` -- :func:`~wte.views.frontend.modules`
    * ``user.modules`` -- ``/users/{uid}/modules`` --
      :func:`~wte.views.frontend.user_modules`
    * ``asset.view`` -- ``/parts/{pid}/files/name/assets/{filename}``
      -- :func:`~wte.views.frontend.view_asset`
    * ``file.view`` -- ``/parts/{pid}/files/name/{filename}``
      -- :func:`~wte.views.frontend.view_file`
    * ``file.save`` -- ``/parts/{pid}/files/id/{fid}/save``
      -- :func:`~wte.views.frontend.save_file`
    * ``part.reset-files`` -- ``/parts/{pid}/reset_files`` --
      :func:`~wte.views.part.reset_files`
    * ``userpartprogress.download`` -- ``/users/{uid}/progress/{pid}/download``
      -- :func:`~wte.views.frontend.download_part_progress`
    """
    config.add_route('modules', '/modules')
    config.add_route('user.modules', '/users/{uid}/modules')
    config.add_route('asset.view', '/parts/{pid}/files/name/assets/{filename}')
    config.add_route('file.view', '/parts/{pid}/files/name/{filename}')
    config.add_route('file.save', '/parts/{pid}/files/id/{fid}/save')
    config.add_route('part.reset-files', '/parts/{pid}/reset_files')
    config.add_route('userpartprogress.download', '/users/{uid}/progress/{pid}/download')


@view_config(route_name='modules')
@render({'text/html': 'part/list.html'})
@current_user()
def modules(request):
    u"""Handles the ``/modules`` URL, displaying all available modules.
    """
    dbsession = DBSession()
    modules = dbsession.query(Part).filter(and_(Part.type == u'module',
                                                Part.status == u'available')).order_by(Part.title).all()
    return {'modules': modules,
            'title': 'Currently Available Modules',
            'missing': 'There are currently no modules available.',
            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules'), 'current': True}]}


@view_config(route_name='user.modules')
@render({'text/html': 'part/list.html'})
@current_user()
@require_logged_in()
def user_modules(request):
    u"""Handles the ``/users/{uid}/modules`` URL, displaying all the
    modules that the  :class:`~wte.models.User` as created or registered for.

    Requires that the current user has "view" rights for the
    :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id == request.matchdict['uid']).first()
    if user:
        if user.allow('view', request.current_user):
            modules = dbsession.query(Part).join(UserPartRole).\
                filter(and_(Part.type == u'module',
                            Part.status.in_([u'available', u'unavailable']),
                            UserPartRole.user_id == request.matchdict[u'uid'])).order_by(Part.title).all()
            modules.extend(dbsession.query(Part).join(UserPartRole).
                           filter(and_(Part.type == u'module',
                                       Part.status == u'archived',
                                       UserPartRole.user_id == request.matchdict[u'uid'])).order_by(Part.title).all())
            return {'modules': modules,
                    'title': 'My Modules',
                    'missing': 'You have not yet created any modules.',
                    'crumbs': [{'title': user.display_name, 'url': request.route_url('user.view', uid=user.id)},
                               {'title': 'Modules',
                                'url': request.route_url('user.modules', uid=request.matchdict['uid']),
                                'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


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
                    headers = [('Content-Type', str(user_file.mimetype))]
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
                        return {'status': 'saved'}
                    else:
                        return {'status': 'no-changes'}
            raise HTTPNotFound()
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.reset-files')
@render({'text/html': 'part/reset_files.html'})
@current_user()
@require_logged_in()
def reset_files(request):
    u"""Handles the ``/parts/{pid}/reset_files`` URL, providing
    the UI and backend for resetting all :class:`~wte.models.Assets` of a
    :class:`~wte.models.Part` to the default for the current user.

    Requires that the user has "view" rights on the current
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Discard all Changes',
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                with transaction.manager:
                    progress = get_user_part_progress(dbsession, request.current_user, part)
                    for user_file in list(progress.files):
                        if 'filename' not in request.params\
                                or request.params['filename'] == user_file.filename:
                            progress.files.remove(user_file)
                            dbsession.delete(user_file)
                raise HTTPSeeOther(request.route_url('part.view',
                                                     pid=request.matchdict['pid']))
            return {'part': part,
                    'crumbs': crumbs}
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
            headerlist = [('Content-Type', str(asset.mimetype))]
            if 'download' in request.params:
                if request.params['download'].lower() == 'true':
                    headerlist.append(('Content-Disposition', str('attachment; filename="%s"' % (asset.filename))))
            return Response(body=asset.data,
                            headerlist=headerlist)
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='userpartprogress.download')
@current_user()
@require_logged_in()
def download_part_progress(request):
    u"""Handles the ``/users/{uid}/progress/{pid}/download``
    URL, sending back the complete set of data associated with the
    :class:`~wte.models.UserPartProgress`.

    Requires that the user has "view" rights on the
    :class:`~wte.models.UserPartProgress`.
    """
    dbsession = DBSession()
    progress = dbsession.query(UserPartProgress).\
        filter(UserPartProgress.id == request.matchdict['pid']).first()
    if progress:
        if progress.allow('view', request.current_user):
            basepath = progress.part.title
            filename = progress.part.title
            parent = progress.part.parent
            while parent:
                basepath = '%s/%s' % (parent.title, basepath)
                filename = '%s - %s' % (parent.title, filename)
                parent = parent.parent
            basepath = '%s/' % (basepath)
            filename = '%s.zip' % (filename)
            body = StringIO()
            zipfile = ZipFile(body, mode='w')
            for user_file in progress.files:
                zipfile.writestr('%s%s' % (basepath, user_file.filename), user_file.data)
            for asset in progress.part.assets:
                zipfile.writestr('%s/assets/%s' % (basepath, asset.filename), asset.data)
            zipfile.close()
            return Response(body=body.getvalue(),
                            headerlist=[('Content-Type', 'application/zip'),
                                        ('Content-Disposition', str('attachment; filename="%s"' % (filename)))])
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
