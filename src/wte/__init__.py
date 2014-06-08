# -*- coding: utf-8 -*-
u"""
######################################
:mod:`wte` -- Web Teaching Environment
######################################

The :mod:`wte` module provides the :func:`~wte.main` function which constructs
the ``WSGIApplication``.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from pywebtools import renderer
from sqlalchemy import engine_from_config

from wte import helpers, views
from wte.models import (DBSession, Base, check_database_version)


def main(global_config, **settings):
    """Constructs, initialises, and returns the Web Teaching Environment's
    ``WSGIApplication``.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    check_database_version()
    settings['genshi.template_path'] = 'wte:templates'
    renderer.init(settings, template_defaults={'text/html': {'h': helpers,
                                                             'crumbs': []}})
    session_factory = session_factory_from_settings(settings)
    config = Configurator(settings=settings, session_factory=session_factory)

    config.add_static_view('static', 'static', cache_max_age=3600)
    views.init(config, settings)

    config.scan()
    return config.make_wsgi_app()
