# -*- coding: utf-8 -*-
u"""
##############################
Unit tests for :mod:`wte.util`
##############################

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from nose.tools import eq_, ok_
from pyramid.httpexceptions import HTTPSeeOther


def version_test():
    u"""Test the basic :data:`wte.util.VERSION` number"""
    from wte.util import VERSION

    eq_('0.99', VERSION)


def state_object_test():
    u"""Test the generic :class:`wte.util.State` object"""
    from wte.util import State

    state = State()
    ok_(state)
    state = State(setting='value')
    ok_(state.setting)
    eq_('value', state.setting)


def unauthorised_redirect_to_login_test():
    u"""Test that :func:`wte.util.unauthorised_redirect` redirects to
    the login page."""
    from wte.models import User
    from wte.util import unauthorised_redirect
    from wte_test import TestRequest, TestSession

    user = User('anonymous@example.com', 'Anyonymous')
    user.logged_in = False
    request = TestRequest(current_url='http://current.url',
                          current_user=user,
                          session=TestSession())
    try:
        unauthorised_redirect(request)
        ok_(False, 'Must not reach this line')
    except HTTPSeeOther as e:
        eq_('http://user.login?return_to=http%3A%2F%2Fcurrent.url', e.location)
        ok_('auth' in request.session.queues)
        eq_(1, len(request.session.queues['auth']))
        eq_('Please log in to access this area.', request.session.queues['auth'][0])


def unauthorised_redirect_to_login_with_message_test():
    u"""Test that :func:`wte.util.unauthorised_redirect` redirects to
    the login page with a custom message."""
    from wte.models import User
    from wte.util import unauthorised_redirect
    from wte_test import TestRequest, TestSession

    user = User('anonymous@example.com', 'Anyonymous')
    user.logged_in = False
    request = TestRequest(current_url='http://current.url',
                          current_user=user,
                          session=TestSession())
    try:
        unauthorised_redirect(request, message='You are not allowed in')
        ok_(False, 'Must not reach this line')
    except HTTPSeeOther as e:
        eq_('http://user.login?return_to=http%3A%2F%2Fcurrent.url', e.location)
        ok_('auth' in request.session.queues)
        eq_(1, len(request.session.queues['auth']))
        eq_('You are not allowed in', request.session.queues['auth'][0])


def unauthorised_redirect_to_root_test():
    u"""Test that :func:`wte.util.unauthorised_redirect` redirects to
    the root page for logged-in users."""
    from wte.models import User
    from wte.util import unauthorised_redirect
    from wte_test import TestRequest, TestSession

    user = User('anonymous@example.com', 'Anyonymous')
    user.logged_in = True
    request = TestRequest(current_url='http://current.url',
                          current_user=user,
                          session=TestSession())
    try:
        unauthorised_redirect(request)
        ok_(False, 'Must not reach this line')
    except HTTPSeeOther as e:
        eq_('http://root', e.location)
        ok_('auth' in request.session.queues)
        eq_(1, len(request.session.queues['auth']))
        eq_('You are not authorised to access this area.', request.session.queues['auth'][0])


def unauthorised_redirect_to_root_with_message_test():
    u"""Test that :func:`wte.util.unauthorised_redirect` redirects to
    the root page for logged-in users with a custom message."""
    from wte.models import User
    from wte.util import unauthorised_redirect
    from wte_test import TestRequest, TestSession

    user = User('anonymous@example.com', 'Anyonymous')
    user.logged_in = True
    request = TestRequest(current_url='http://current.url',
                          current_user=user,
                          session=TestSession())
    try:
        unauthorised_redirect(request, message='You are not allowed in')
        ok_(False, 'Must not reach this line')
    except HTTPSeeOther as e:
        eq_('http://root', e.location)
        ok_('auth' in request.session.queues)
        eq_(1, len(request.session.queues['auth']))
        eq_('You are not allowed in', request.session.queues['auth'][0])


def unauthorised_redirect_to_location_test():
    u"""Test that :func:`wte.util.unauthorised_redirect` redirects to
    a custom page for logged-in users."""
    from wte.models import User
    from wte.util import unauthorised_redirect
    from wte_test import TestRequest, TestSession

    user = User('anonymous@example.com', 'Anyonymous')
    user.logged_in = True
    request = TestRequest(current_url='http://current.url',
                          current_user=user,
                          session=TestSession())
    try:
        unauthorised_redirect(request, redirect_to='http://target.url')
        ok_(False, 'Must not reach this line')
    except HTTPSeeOther as e:
        eq_('http://target.url', e.location)
        ok_('auth' in request.session.queues)
        eq_(1, len(request.session.queues['auth']))
        eq_('You are not authorised to access this area.', request.session.queues['auth'][0])


def send_email_no_config_test():
    u"""Tests that :func:`wte.util.send_email` works if no "email.smtp_host"
    is set."""
    from wte.util import send_email, State, CACHED_SETTINGS
    from wte_test import TestRequest

    CACHED_SETTINGS.clear()
    request = TestRequest(registry=State(settings={}))
    send_email(request,
               'receiver@example.com',
               'sender@example.com',
               'Test E-Mail',
               'This is the text of the e-mail')
    ok_(True)


def send_email_fail_test():
    u"""Tests that :func:`wte.util.send_email` works when an invalid "email.smtp_host"
    is set."""
    from wte.util import send_email, State, CACHED_SETTINGS
    from wte_test import TestRequest

    CACHED_SETTINGS.clear()
    request = TestRequest(registry=State(settings={'email.smtp_host': 'localhost:76543'}))
    send_email(request,
               'receiver@example.com',
               'sender@example.com',
               'Test E-Mail',
               'This is the text of the e-mail')
    ok_(True)


def convert_type_test():
    u"""Tests the basic conversion using :func:`wte.util.convert_type`."""
    from wte.util import convert_type

    eq_('input', convert_type('input', 'string'))
    eq_(None, convert_type(None, 'string', default=None))
    eq_('default', convert_type(None, 'string', default='default'))


def convert_type_int_test():
    u"""Tests integer conversion using :func:`wte.util.convert_type`."""
    from wte.util import convert_type

    eq_(1, convert_type('1', 'int'))
    eq_(None, convert_type('a', 'int'))
    eq_(0, convert_type('a', 'int', default=0))


def convert_type_bool_test():
    u"""Tests boolean conversion using :func:`wte.util.convert_type`."""
    from wte.util import convert_type

    eq_(True, convert_type('true', 'boolean'))
    eq_(True, convert_type('True', 'boolean'))
    eq_(False, convert_type('false', 'boolean'))
    eq_(False, convert_type('False', 'boolean'))


def get_config_setting_test():
    u"""Tests getting configuration settings using
    :func:`wte.util.get_config_setting`."""
    from wte.util import CACHED_SETTINGS, get_config_setting, State
    from wte_test import TestRequest

    request = TestRequest(registry=State(settings={'test': 'Test',
                                                   'number': '1'}))
    CACHED_SETTINGS.clear()
    eq_(0, len(CACHED_SETTINGS))
    eq_('Test', get_config_setting(request, 'test'))
    eq_(1, len(CACHED_SETTINGS))
    eq_('Test', get_config_setting(request, 'test'))
    eq_(1, len(CACHED_SETTINGS))
    eq_(1, get_config_setting(request, 'number', target_type='int'))
    eq_(2, len(CACHED_SETTINGS))
    eq_(1, get_config_setting(request, 'number', target_type='int'))
    eq_(2, len(CACHED_SETTINGS))
    eq_(True, get_config_setting(request, 'switch', target_type='boolean', default=True))
    eq_(3, len(CACHED_SETTINGS))
