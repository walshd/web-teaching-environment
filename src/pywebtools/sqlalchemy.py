# -*- coding: utf-8 -*-
"""
#################################################################
:mod:`pywebtools.sqlalchemy` -- Utilities for use with SQLAlchemy
#################################################################

This module provide the generic ``DBSession`` :class:`~sqlalchemy.orm.scoped_session`
for use with Pyramid & SQLAlchemy. It also provides the ``Base``
:func:`~sqlalchemy.ext.declarative.declarative_base` that acts as the base class
for any declarative model. If you are starting from a SQLAlchemy + Pyramid starter
template in your ``models`` module, remove the ``DBSession`` and ``Base`` and
replace them imports from this module. Then do the same for the ``main`` function
in the main package.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from sqlalchemy import text
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (scoped_session, sessionmaker)
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class DBUpgradeException(Exception):
    """The :class:`~pywebtools.sqlalchemy.DBUpgradeException` is used to indicate that
    the database requires an upgrade before the Web Teaching Environment system
    can be used.
    """
    def __init__(self, current, required):
        self.current = current
        self.required = required

    def __repr__(self):
        return "DBUpgradeException('%s', '%s'" % (self.current, self.required)

    def __str__(self):
        return "A database upgrade is required.\n\n" + \
            "You are currently running version '%s', but version '%s' is " % (self.current, self.required) + \
            " required. Please run WTE update-database config.ini upgrade to upgrade the database " + \
            "and then start the application again."


def check_database_version(db_version):
    """Checks that the current version of the database matches the version specified
    by ``db_version``. This requires the use of the Alembic database migration library.

    :param db_version: The version identifier to check.
    :type db_version: ``str``
    """
    dbsession = DBSession()
    try:
        inspector = Inspector.from_engine(dbsession.bind)
        if 'alembic_version' in inspector.get_table_names():
            result = dbsession.query('version_num').\
                from_statement(text('SELECT version_num FROM alembic_version WHERE version_num = :version_num')).\
                params(version_num=db_version).first()
            if not result:
                result = dbsession.query('version_num').\
                    from_statement('SELECT version_num FROM alembic_version').first()
                raise DBUpgradeException(result[0], db_version)
    except OperationalError:
        raise DBUpgradeException('No version-information found', db_version)
