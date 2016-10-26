# -*- coding: utf-8 -*-
"""
#################################################################
:mod:`wte.scripts.configuration` -- Generate configuration script
#################################################################

The :mod:`~wte.scripts.configuration` module provides the functionality for
generating a configuration file from the default template and generating new
styles.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import uuid

from kajiki import TextTemplate
from pkg_resources import resource_string

from wte.scripts.main import get_user_parameter


def init(subparsers):
    """Initialises the :class:`~argparse.ArgumentParser`, adding the
    "generate-config" and "generate-custom-styling" commands.
    """
    parser = subparsers.add_parser('generate-config', help='Generate the WTE configuration file')
    parser.add_argument('--filename', default='production.ini', help='Configuration file name')
    parser.add_argument('--sqla-connection-string', default=None, help='SQLAlchemy database connection string')
    parser.set_defaults(func=generate_config)


def generate_config(args):
    """Generates a configuration file based on the default_config.txt template.
    """
    tmpl = TextTemplate(resource_string('wte', 'scripts/templates/default_config.txt').decode('utf-8'))
    params = {'encrypt_key': uuid.uuid1(),
              'validate_key': uuid.uuid1()}
    if args.sqla_connection_string:
        params['sqlalchemy_url'] = args.sqla_connection_string
    else:
        params['sqlalchemy_url'] = get_user_parameter('SQL Alchemy Connection String', 'sqlite:///%(here)s/wte_test.db')

    with open(args.filename, 'w') as out_f:
        out_f.write(tmpl(params).render())
