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
from pywebtools import renderer
from sqlalchemy import engine_from_config

from wte import helpers, views, text_formatter
from wte.models import (DBSession, Base, check_database_version)


def main(global_config, **settings):
    """Constructs, initialises, and returns the Web Teaching Environment's
    ``WSGIApplication``.
    """
    # Init Database
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    check_database_version()
    # Init rendering
    settings['genshi.template_path'] = 'wte:templates'
    renderer.init(settings, template_defaults={'text/html': {'h': helpers,
                                                             'crumbs': [],
                                                             'include_footer': True}})
    # Init configuration
    config = Configurator(settings=settings)
    config.include('kajiki.integration.pyramid')
    # Init routes
    config.add_static_view('static', 'static', cache_max_age=3600)
    views.init(config, settings)
    # Init docutils
    text_formatter.init(settings)

    config.scan()
    return config.make_wsgi_app()
