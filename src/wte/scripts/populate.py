# -*- coding: utf-8 -*-
import transaction

from pkg_resources import resource_stream
from pyramid.paster import (get_appsettings, setup_logging)
from sqlalchemy import engine_from_config

from wte.models import (Base, DBSession, Module, Tutorial, Page,
                        User, Permission, PermissionGroup)

def init(subparsers):
    parser = subparsers.add_parser('initialise-database', help='Initialise the database')
    parser.add_argument('configuration', help='WTE configuration file')
    parser.add_argument('--drop-existing', action='store_true', default=False, help='Drop any existing tables')
    parser.set_defaults(func=initialise_database)

def initialise_database(args):
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    if args.drop_existing:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    DBSession.configure(bind=engine)
    dbsession = DBSession()
    with transaction.manager:
        group = PermissionGroup(title=u'User Admin')
        dbsession.add(group)
        group.permissions.append(Permission(name=u'admin.users.view', title=u'View all users'))
        group.permissions.append(Permission(name=u'admin.users.edit', title=u'Edit all users'))
        group.permissions.append(Permission(name=u'admin.users.delete', title=u'Delete all users'))
        group.permissions.append(Permission(name=u'admin.users.permissions', title=u'Edit user permissions'))
        
        admin_user = User(email=u'admin@example.com', display_name=u'Admin', password=u'password')
        admin_user.permission_groups.append(group)
        
