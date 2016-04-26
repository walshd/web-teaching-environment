# -*- coding: utf-8 -*-
"""
######################################################
:mod:`wte.scripts.main` -- Administration application
######################################################

The :mod:`~wte.scripts.main` module contains the core of the administration
application ``WTE``, via the :func:`~wte.scripts.main.main` function.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from argparse import ArgumentParser


def get_user_parameter(prompt, default=''):
    """The :func:`~wte.scripts.main.get_user_parameter` function provides a
    generic helper function that prompts the user for a value.

    :param prompt: The prompt to display to the user
    :type prompt: `unicode`
    :param default: The default value to return if the user does not provide
                    a value
    :type default: `unicode`
    :return: The user's input
    :rtype: `unicode`
    """
    if default:
        prompt = '%s [%s]: ' % (prompt, default)
    else:
        prompt = '%s: ' % (prompt)
    response = input(prompt)
    if response.strip() == '':
        return default
    else:
        return response


def main():
    """The :func:`~wte.scripts.main.main` function handles the creation of
    the :class:`~argparse.ArgumentParser` that processes the administrative
    application's command-line parameters. It calls the ``init()`` functions
    on the modules that implement the actual functionality to build up the
    complete parser and then calls the appropriate function for the command
    the user provided on the command-line.
    """
    from . import configuration, database, timed_tasks

    parser = ArgumentParser(description='WTE administration application')
    subparsers = parser.add_subparsers()

    configuration.init(subparsers)
    database.init(subparsers)
    timed_tasks.init(subparsers)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_usage()
