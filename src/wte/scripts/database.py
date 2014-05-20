# -*- coding: utf-8 -*-
u"""
################################################
:mod:`wte.scripts.database` -- Database  scripts
################################################

The :mod:`~wte.scripts.database` module provides the functionality for
creating the initial database.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import transaction

from pkg_resources import resource_stream
from pyramid.paster import (get_appsettings, setup_logging)
from sqlalchemy import engine_from_config

from wte.models import (Base, DBSession, Module, Tutorial, Page,
                        User, Permission, PermissionGroup)

def init(subparsers):
    u"""Initialises the :class:`~argparse.ArgumentParser`, adding the
    "initialise-database" command.
    """
    parser = subparsers.add_parser('initialise-database', help='Initialise the database')
    parser.add_argument('configuration', help='WTE configuration file')
    parser.add_argument('--drop-existing', action='store_true', default=False, help='Drop any existing tables')
    parser.set_defaults(func=initialise_database)

def initialise_database(args):
    u"""Initialises the database schema and adds the default
    :class:`~wte.models.Permission`, :class:`~wte.models.PermissionGroup`, and
    :class:`~wte.models.User` to the database.
    """
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    if args.drop_existing:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    DBSession.configure(bind=engine)
    dbsession = DBSession()
    with transaction.manager:
        admin_user = User(email=u'admin@example.com', display_name=u'Admin', password=u'password')
        dbsession.add(admin_user)
        
        group = PermissionGroup(title=u'User Admin')
        dbsession.add(group)
        group.permissions.append(Permission(name=u'admin.users.view', title=u'View all users'))
        group.permissions.append(Permission(name=u'admin.users.edit', title=u'Edit all users'))
        group.permissions.append(Permission(name=u'admin.users.delete', title=u'Delete all users'))
        group.permissions.append(Permission(name=u'admin.users.permissions', title=u'Edit user permissions'))
        admin_user.permission_groups.append(group)
        
        group = PermissionGroup(title=u'Content Admin')
        dbsession.add(group)
        create_module_perm = Permission(name=u'modules.create', title=u'Create a new module')
        group.permissions.append(create_module_perm)
        group.permissions.append(Permission(name=u'admin.modules.view', title=u'View all modules'))
        group.permissions.append(Permission(name=u'admin.modules.edit', title=u'Edit all modules'))
        group.permissions.append(Permission(name=u'admin.modules.delete', title=u'Delete all modules'))
        admin_user.permission_groups.append(group)

        group = PermissionGroup(title=u'Teacher')
        dbsession.add(group)
        group.permissions.append(create_module_perm)
