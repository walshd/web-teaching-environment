# -*- coding: utf-8 -*-
u"""
#################################################################
:mod:`wte.scripts.configuration` -- Generate configuration script
#################################################################

The :mod:`~wte.scripts.configuration` module provides the functionality for
generating a configuration file from the default template and generating new
styles.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import sass
import uuid

from genshi.template import TemplateLoader, loader, NewTextTemplate
from os import path
from pkg_resources import resource_filename, resource_exists
from pygments import formatters, styles
from pyramid.paster import get_appsettings

from wte.scripts.main import get_user_parameter


def init(subparsers):
    u"""Initialises the :class:`~argparse.ArgumentParser`, adding the
    "generate-config" and "generate-custom-styling" commands.
    """
    parser = subparsers.add_parser('generate-config', help='Generate the WTE configuration file')
    parser.add_argument('--filename', default='production.ini', help='Configuration file name')
    parser.add_argument('--sqla-connection-string', default=None, help='SQLAlchemy database connection string')
    parser.set_defaults(func=generate_config)
    parser = subparsers.add_parser('generate-custom-styling', help='Generate custom CSS styling')
    parser.add_argument('configuration', default='production.ini', help='Configuration file name')
    parser.set_defaults(func=generate_custom_styling)


def generate_config(args):
    u"""Generates a configuration file based on the default_config.txt template.
    """
    tmpl_loader = TemplateLoader([loader.package('wte', 'scripts/templates/')])
    tmpl = tmpl_loader.load('default_config.txt', cls=NewTextTemplate)
    params = {'encrypt_key': uuid.uuid1(),
              'validate_key': uuid.uuid1()}
    if args.sqla_connection_string:
        params['sqlalchemy_url'] = args.sqla_connection_string
    else:
        params['sqlalchemy_url'] = get_user_parameter('SQL Alchemy Connection String', 'sqlite:///%(here)s/wte_test.db')

    with open(args.filename, 'w') as out_f:
        for data in tmpl.generate(**params).render('text'):
            out_f.write(data)


def generate_custom_styling(args):
    u"""Generates a custom CSS styling for the WTE application. Allows
    customisation of general settings, Pygments style, and CodeMirror theme.
    """
    settings = get_appsettings(args.configuration)

    # Create the settings overide partial
    with open(resource_filename('wte', 'static/scss/_settings.scss'), 'w') as out_f:
        out_f.write('/* Any changes made here will be automatically overwritten */\n')
        if 'style.settings' in settings and path.exists(settings['style.settings']):
            with open(settings['style.settings']) as in_f:
                out_f.write(in_f.read())

    # Create the Pygments partial
    pygments_style = 'default'
    if 'pygments.theme' in settings and settings['pygments.theme'] in list(styles.get_all_styles()):
        pygments_style = settings['pygments.theme']
    with open(resource_filename('wte', 'static/scss/application/_pygments.scss'), 'w') as out_f:
        out_f.write('/* Any changes made here will be automatically overwritten */\n')
        out_f.write(formatters.HtmlFormatter(style=pygments_style).get_style_defs())

    # Create the CodeMirror theme partial
    codemirror_theme = None;
    if 'codemirror.theme' in settings:
        if resource_exists('wte', 'static/css/codemirror/theme/%s.css' % (settings['codemirror.theme'])):
            codemirror_theme = settings['codemirror.theme']
    with open(resource_filename('wte', 'static/scss/codemirror/_theme.scss'), 'w') as out_f:
        out_f.write('/* Any changes made here will be automatically overwritten */\n')
        if codemirror_theme:
            with open(resource_filename('wte', 'static/scss/codemirror/theme/%s.css' % (codemirror_theme))) as in_f:
                out_f.write(in_f.read())

    # Create the final overide partial
    with open(resource_filename('wte', 'static/scss/_overrides.scss'), 'w') as out_f:
        out_f.write('/* Any changes made here will be automatically overwritten */\n')
        if 'style.settings' in settings and path.exists(settings['style.overrides']):
            with open(settings['style.overrides']) as in_f:
                out_f.write(in_f.read())

    # Generate application.min.css
    css = sass.compile(filename=resource_filename('wte', 'static/scss/wte.scss'),
                       output_style='compressed',
                       custom_functions={'file-exists': lambda fn: False})
    with open(resource_filename('wte', 'static/css/application.min.css'), 'w') as out_f:
        out_f.write(css)
