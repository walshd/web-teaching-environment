# -*- coding: utf-8 -*-
u"""
#########################
Unit tests for :mod:`wte`
#########################

This module also contains some generic objects for use in testing the WTE.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from urllib import urlencode


class TestRequest(object):
    u"""The :class:`wte_test.TestRequest` is a test request object that
    implements the functions needed for testing requests
    """

    def __init__(self, **kwargs):
        u"""Any parameters passed to the constructor are automatically set as
        attributes of the :class:`~wte.util.TestRequest`.
        """
        self.__dict__.update(kwargs)

    def route_url(self, name, *elements, **keywords):
        u"""Generates a URL http://{name}/{elements}?{keywords['_query']}."""
        url = 'http://%s' % (name)
        if elements:
            url = '%s/%s' % (url, '/'.join(elements))
        if '_query' in keywords:
            if isinstance(keywords['_query'], dict):
                url = '%s?%s' % (url, urlencode(keywords['_query'].items()))
            else:
                url = '%s?%s' % (url, urlencode(keywords['_query']))
        return url

    def current_route_url(self):
        u"""Returns the value of the ``current_url`` attribute if it exists."""
        if hasattr(self, 'current_url'):
            return self.current_url
        else:
            return None


class TestSession(object):
    u"""The :class:`~wte_test.TestSession` is a test session for requests that
    need access to a session."""

    def __init__(self):
        self.queues = {'': []}

    def flash(self, message, queue=None):
        u"""Add a flash message to the internal queue of messages."""
        if queue:
            if queue in self.queues:
                self.queues[queue].append(message)
            else:
                self.queues[queue] = [message]
        else:
            self.queues[''] = message
