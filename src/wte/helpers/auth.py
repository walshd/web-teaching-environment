# -*- coding: utf-8 -*-
u"""
##########################################################
:mod:`wte.helpers.auth` -- Authentication helper functions
##########################################################

The mod:`~wte.helpers.auth` module provides helper functions for use with
authentication. It also imports the :mod:`pywebtools.auth` module as
``engine``.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""

from pywebtools import auth as engine

def is_authorised(user, action, obj):
    u"""The :func:`~wte.helpers.auth.is_authorised` function checks if the
    given ``user`` is authorised to perform the ``action`` on the given
    ``obj``.
    
    :param user: The user to check authorisation for
    :type user: :class:`wte.models.User`
    :param action: The action to check authorisation for
    :type action: `unicode`
    :param obj: The object to check authorisation for
    :return: ``True`` if the user is authorised, ``False`` otherwise
    :rtype: `bool`
    """
    return engine.is_authorised(':obj.allow("%s" :user)' % (action), {'obj': obj, 'user': user})
