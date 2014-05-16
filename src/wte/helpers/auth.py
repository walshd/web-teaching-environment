# -*- coding: utf-8 -*-
u"""

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""

from pywebtools import auth as engine

def is_authorised(user, action, obj):
    return engine.is_authorised(':obj.allow("%s" :user)' % (action), {'obj': obj, 'user': user})
