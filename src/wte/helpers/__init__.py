# -*- coding: utf-8 -*-
u"""
####################################################
:mod:`wte.helpers` -- Helper functionality for views
####################################################

The :mod:`~wte.helpers` module imports various helper modules that can be used
in the templates via the ``h`` variable. For details of the functions available
consulte the following documentation: :mod:`pywebtools.text`,
:mod:`wte.helpers.auth`, and :mod:`wte.helpers.form`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""

from genshi.builder import Markup  # NOQA
from pywebtools import text  # NOQA

from . import form, frontend  # NOQA
from wte.util import VERSION


def version():
    return VERSION
