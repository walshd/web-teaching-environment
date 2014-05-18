# -*- coding: utf-8 -*-
u"""
#################################################################
:mod:`wte.scripts.configuration` -- Generate configuration script
#################################################################

The :mod:`~wte.scripts.configuration` module provides the functionality for
generating a configuration file from the default template.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import uuid
from genshi.template import TemplateLoader, loader, NewTextTemplate

from wte.scripts.main import get_user_parameter

def init(subparsers):
    u"""Initialises the :class:`~argparse.ArgumentParser`, adding the
    "generate-config" command.
    """
    parser = subparsers.add_parser('generate-config', help='Generate the WTE configuration file')
    parser.add_argument('--filename', default='production.ini', help='Configuration file name')
    parser.add_argument('--sqla-connection-string', default=None, help='SQLAlchemy database connection string')
    parser.set_defaults(func=generate_config)
    
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
    