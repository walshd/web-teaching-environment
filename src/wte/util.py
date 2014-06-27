# -*- coding: utf-8 -*-
u"""
###########################################
:mod:`wte.models.util` -- Utility functions
###########################################

The :mod:`~wte.models.util` module provides various utility objects and
functions.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import logging
import smtplib

from pyramid.httpexceptions import HTTPSeeOther
from email.mime.text import MIMEText
from email.utils import formatdate


class State(object):
    u"""The :class:`~wte.util.State` provides a blank state object for use
    with Formencode validation. Any parameters passed to the constructor are
    automatically set as attributes of the :class:`~wte.util.State`.
    """

    def __init__(self, **kwargs):
        u"""Any parameters passed to the constructor are automatically set as
        attributes of the :class:`~wte.util.State`.
        """
        self.__dict__.update(kwargs)


def unauthorised_redirect(request, redirect_to=None):
    """Provides standardised handling of "unauthorised" redirection. Depending
    on whether the user is currently logged in, it will set the appropriate
    error message into the session flash and redirect to the appropriate page.
    If the user is logged in, it will redirect to the root page or to the
    ``redirect_to`` URL if specified. If the user is not logged in, it will
    always redirect to the login page.

    :param request: The pyramid request
    :param redirect_to: The URL to redirect to, if the user is currently
                        logged in.
    :type redirect_to: `unicode`
    """
    if request.current_user.logged_in:
        request.session.flash('You are not authorised to access this area.', queue='auth')
        if redirect_to:
            raise HTTPSeeOther(redirect_to)
        else:
            raise HTTPSeeOther(request.route_url('root'))
    else:
        request.session.flash('Please log in to access this area.', queue='auth')
        raise HTTPSeeOther(request.route_url('user.login', _query={'return_to': request.current_route_url()}))


def send_email(request, recipient, sender, subject, text):
    u"""Sends an e-mail based on the settings in the configuration file. If
    the configuration does not have e-mail settings or if there is an
    exception sending the e-mail, then it will log an error.

    :param request: The current request used to access the settings
    :type request: :class:`pyramid.request.Request`
    :param recipient: The recipient's e-mail address
    :type recipient: `unicode`
    :param sender: The sender's e-mail address
    :type sender: `unicode`
    :param subject: The e-mail's subject line
    :type subject: `unicode`
    :param text: The e-mail's text body content
    :type text: `unicode`
    """
    if get_config_setting(request, 'email.smtp_host'):
        email = MIMEText(text)
        email['Subject'] = subject
        email['From'] = sender
        email['To'] = recipient
        email['Date'] = formatdate()
        try:
            smtp = smtplib.SMTP(get_config_setting(request, 'email.smtp_host'))
            if get_config_setting(request, 'email.ssl', target_type='bool', default=False):
                smtp.starttls()
            username = get_config_setting(request, 'email.username')
            password = get_config_setting(request, 'email.password')
            if username and password:
                smtp.login(username, password)
            smtp.sendmail(sender, recipient, email.as_string())
            smtp.quit()
        except Exception as e:
            logging.getLogger("wte").error(unicode(e))
            print text  # TODO: Remove
    else:
        logging.getLogger("wte").error('Could not send e-mail as "email.smtp_host" setting not specified')


def convert_type(value, target_type, default=None):
    u"""Attempts to convert the ``value`` to the given ``target_type``. Will
    return ``default`` if the conversion fails.

    Supported ``target_type`` values are:

    * `int` -- Convert to an integer value
    * `boolean` -- Convert to a boolean value (``True`` if the value is the
      ``unicode`` string "true" in any capitalisation

    :param value: The value to convert
    :type value: `unicode`
    :param target_type: The target type to convert to
    :type target_type: `unicode`
    :param default: The default value if the conversion fails
    :return: The converted value
    """
    if target_type == 'int':
        try:
            return int(value)
        except ValueError:
            return default
    elif target_type == 'boolean':
        if value and value.lower() == 'true':
            return True
        else:
            return False
    if value:
        return value
    else:
        return default


CACHED_SETTINGS = {}


def get_config_setting(request, key, target_type=None, default=None):
    u"""Gets a configuration setting from the application configuration.
    Settings are cached for faster access.

    :param request: The request used to access the configuration settings
    :type request: :class:`~pyramid.request.Request`
    :param key: The configuration key
    :type key: `unicode`
    :param target_type: If specified, will convert the configuration setting
                        to the given type using :func:`~wte.util.convert_type`
    :type default: The default value to return if there is no setting with the
                   given key
    :return: The configuration setting value or ``default``
    """
    global CACHED_SETTINGS
    if key in CACHED_SETTINGS:
        return CACHED_SETTINGS[key]
    else:
        if key in request.registry.settings:
            if target_type:
                CACHED_SETTINGS[key] = convert_type(request.registry.settings[key], target_type, default=default)
            else:
                CACHED_SETTINGS[key] = request.registry.settings[key]
        else:
            CACHED_SETTINGS[key] = default
        return get_config_setting(request, key, target_type=target_type, default=default)
