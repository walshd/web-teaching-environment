# -*- coding: utf-8 -*-
"""
################################################
:mod:`wte.scripts.database` -- Database  scripts
################################################

The :mod:`~wte.scripts.database` module provides the functionality for
creating the initial database.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import transaction

from alembic import config, command
from pyramid.paster import (get_appsettings, setup_logging)
from sqlalchemy import engine_from_config

from wte.models import (Base, DBSession, User, Permission, PermissionGroup,
                        DB_VERSION)


def init(subparsers):
    """Initialises the :class:`~argparse.ArgumentParser`, adding the
    "initialise-database" command.
    """
    parser = subparsers.add_parser('initialise-database', help='Initialise the database')
    parser.add_argument('configuration', help='WTE configuration file')
    parser.add_argument('--drop-existing', action='store_true', default=False, help='Drop any existing tables')
    parser.set_defaults(func=initialise_database)
    parser = subparsers.add_parser('update-database', help='Update the Web Teaching Environment database')
    parser.add_argument('configuration', help='Configuration file')
    parser.set_defaults(func=update_database)
    parser = subparsers.add_parser('downgrade-database', help='Downgrade the Web Teaching Environment database')
    parser.add_argument('configuration', help='Configuration file')
    parser.set_defaults(func=downgrade_database)


def initialise_database(args):
    """Initialises the database schema and adds the default
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
        admin_user = User(email='admin@example.com', display_name='Admin', password='password')
        dbsession.add(admin_user)

        admin_permission = Permission(name='admin', title='Administration Access')

        group = PermissionGroup(title='User Administration')
        dbsession.add(group)
        group.permissions.append(admin_permission)
        group.permissions.append(Permission(name='admin.users.view', title='View all users'))
        group.permissions.append(Permission(name='admin.users.edit', title='Edit all users'))
        group.permissions.append(Permission(name='admin.users.delete', title='Delete all users'))
        group.permissions.append(Permission(name='admin.users.permissions', title='Edit user permissions'))
        admin_user.permission_groups.append(group)

        group = PermissionGroup(title='Content Administration')
        dbsession.add(group)
        group.permissions.append(admin_permission)
        create_module_perm = Permission(name='modules.create', title='Create a new module')
        group.permissions.append(create_module_perm)
        group.permissions.append(Permission(name='admin.modules.view', title='View all modules'))
        group.permissions.append(Permission(name='admin.modules.edit', title='Edit all modules'))
        group.permissions.append(Permission(name='admin.modules.delete', title='Delete all modules'))
        admin_user.permission_groups.append(group)

        group = PermissionGroup(title='Teacher')
        dbsession.add(group)
        group.permissions.append(create_module_perm)

        group = PermissionGroup(title='Student')
        dbsession.add(group)


def update_database(args):
    alembic_config = config.Config(args.configuration, ini_section='app:main')
    alembic_config.set_section_option('app:main', 'script_location', 'wte:migrations')
    command.upgrade(alembic_config, DB_VERSION)


def downgrade_database(args):
    alembic_config = config.Config(args.configuration, ini_section='app:main')
    alembic_config.set_section_option('app:main', 'script_location', 'wte:migrations')
    command.downgrade(alembic_config, '-1')
