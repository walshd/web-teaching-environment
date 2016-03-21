# -*- coding: utf-8 -*-
u"""
####################################
:mod:`wte.util` -- Utility functions
####################################

The :mod:`~wte.util` module provides various utility objects and
functions.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import asset
import formencode
import logging
import math
import smtplib

from datetime import datetime
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


class CSRFValidator(formencode.FancyValidator):
    """Validator that checks a value against the Cross-Site Request Forgery
    token stored in the user's session."""

    messages = {'invalid_csrf_token': 'The CSRF token is invalid. This might indicate a malicious attack.',
                'missing': 'No CSRF token was provided. This might indicate a malicious attack.',
                'empty': 'An empty CSRF token was provided. This might indicate a malicious attack.'}

    def _validate_python(self, value, state):
        """If a :pyramid:class:`request.Request` is set in the ``state``, then
        checks whether the ``value`` matches the CSRF token stored in the request.
        """
        if hasattr(state, 'request'):
            if state.request.session.get_csrf_token() != value:
                raise formencode.Invalid(self.message('invalid_csrf_token', state),
                                         value,
                                         state)


class CSRFSchema(formencode.Schema):
    """The class:`wte.util.CSRFSchema` is a base :class:`formencode.Schema`
    that includes Cross-Site Request Forgery detection.

    It should be used as the base class for all specific request schemas.
    """

    csrf_token = CSRFValidator(strip=True, not_empty=True)


class DynamicSchema(formencode.Schema):
    u"""The :class:`~wte.util.DynamicSchema` provides a dynamic
    :class:`~formencode.schema.Schema` for which the validation fields are
    defined from the ``list`` of (field-name,
    :class:`~formencode.api.FancyValidator`) pairs passed to the
    constructor.
    """
    accept_iterator = True

    def __init__(self, fields=None, **kwargs):
        formencode.Schema.__init__(self, **kwargs)
        if fields:
            for (name, validator) in fields:
                self.add_field(name, validator)


class DateValidator(formencode.FancyValidator):
    u"""The :class:`~wte.util.DateValidator` provides date validation and
    conversion from the formats "YYYY-MM-DD" or "DD/MM/YYYY" to a python
    :class:`datetime.date`.
    """

    messages = {'invalid_format': 'Please enter a date either as YYYY-MM-DD or DD/MM/YYYY'}

    def _convert_to_python(self, value, state):
        u"""Try to convert from either "YYYY-MM-DD" or "DD-MM-YYYY" to a
        :class:`datetime.date`. Raises :class:`~formencode.api.Invalid` if the
        conversion fails.

        :param value: The `unicode` value to convert
        :param type: `unicode`
        :return: The converted date
        :return_type: :class:`datetime.date`.
        """
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except:
            try:
                return datetime.strptime(value, '%d/%m/%Y').date()
            except:
                raise formencode.api.Invalid(self.message('invalid_format', state), value, state)


class TimeValidator(formencode.FancyValidator):
    u"""The :class:`~wte.util.DateValidator` provides time validation and
    conversion from the format "HH:MM" to a python :class:`datetime.time`.
    """

    messages = {'invalid_format': 'Please enter a time as HH:MM'}

    def _convert_to_python(self, value, state):
        u"""Try to convert from "HH:MM" to a :class:`datetime.time`. Raises
        :class:`~formencode.api.Invalid` if the conversion fails.

        :param value: The `unicode` value to convert
        :param type: `unicode`
        :return: The converted time
        :return_type: :class:`datetime.time`
        """
        try:
            return datetime.strptime(value, '%H:%M').time()
        except Exception as e:
            print(e)
            raise formencode.api.Invalid(self.message('invalid_format', state), value, state)


def unauthorised_redirect(request, redirect_to=None, message=None):
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
    :param message: The message to show to the user
    :type message: ``unicode``
    """
    if request.current_user.logged_in:
        if message:
            request.session.flash(message, queue='auth')
        else:
            request.session.flash('You are not authorised to access this area.', queue='auth')
        if redirect_to:
            raise HTTPSeeOther(redirect_to)
        else:
            raise HTTPSeeOther(request.route_url('root'))
    else:
        if message:
            request.session.flash(message, queue='auth')
        else:
            request.session.flash('Please log in to access this area.', queue='auth')
        raise HTTPSeeOther(request.route_url('user.login', _query={'return_to': request.current_route_url()}))


def send_email(request, recipient, sender, subject, text):  # pragma: no cover
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
            print(text)  # TODO: Remove
    else:
        logging.getLogger("wte").error('Could not send e-mail as "email.smtp_host" setting not specified')
        print(text)  # TODO: Remove


def convert_type(value, target_type, default=None):
    u"""Attempts to convert the ``value`` to the given ``target_type``. Will
    return ``default`` if the conversion fails.

    Supported ``target_type`` values are:

    * `int` -- Convert to an integer value
    * `boolean` -- Convert to a boolean value (``True`` if the value is the
      ``unicode`` string "true" in any capitalisation
    * `list` -- Convert to a list, splitting on line-breaks and commas

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
    elif target_type == 'list':
        return [v.strip() for line in value.split('\n') for v in line.split(',')]
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


def version():
    """Return the current application version."""
    return asset.version('WebTeachingEnvironment')


def timing_tween_factory(handler, registry):
    """Pyramid tween factory that logs the time taken for a request.
    Will not time static requests.
    """
    import time
    logger = logging.getLogger(__name__)

    def timing_tween(request):
        """Handle the actual timing of the request."""
        start = time.time()
        try:
            response = handler(request)
        finally:
            end = time.time()
            if not request.path.startswith('/static'):
                logger.info('%s - %.4f seconds' % (request.path, (end - start)))
        return response
    return timing_tween


def paginate(request, query, start, rows, query_params=None):
    """Generates the list of pages for a query.

    :param request: The request used to generate URLs
    :type request: :class:`~pyramid.request.Request`
    :param query: The SQLAlchemy query to generate the pagination for
    :type query: :class:`~sqlalchemy.orm.query.Query`
    :param start: The current starting index
    :type start: :py:func:`int`
    :param rows: The number of rows per page
    :type rows: :py:func:`int`
    :param query_params: An optional list of query parameters to include in all
                         URLs that are generated
    :type query_params: :py:func:`list` of :py:func:`tuple`
    :return: The :py:func:`list` of pages to use with the "navigation.pagination"
             helper
    :rtype: :py:func:`list`
    """
    if query_params is None:
        query_params = []
    else:
        query_params = [param for param in query_params if param[0] != 'start']
    count = query.count()
    pages = []
    if start > 0:
        pages.append({'type': 'prev',
                      'url': request.route_url('users', _query=query_params + [('start', max(start - rows, 0))])})
    else:
        pages.append({'type': 'prev'})
    for idx in range(0, int(math.ceil(count / float(rows)))):
        if idx == (start / 30):
            pages.append({'type': 'current',
                          'label': unicode(idx + 1)})
        else:
            pages.append({'type': 'item',
                          'label': unicode(idx + 1),
                          'url': request.route_url('users', _query=query_params + [('start', idx * rows)])})
    if start + rows < count:
        pages.append({'type': 'next',
                      'url': request.route_url('users', _query=query_params + [('start', max(start + rows, count))])})
    else:
        pages.append({'type': 'next'})
    return pages


def ordered_counted_set(items):
    """Returns a list of ``(item, count)`` tuples derived from the ``items``.
    Each unique item is listed once with the number of times it appears in
    the ``items`` The unique items are ordered in the same order in which
    they appear in the ``items``.
    
    :param items: The list of items to create the ordered, counted set for
    :type items: :func:`list`
    :return: A list of unique items with their frequency counts
    :r_type: :func:`list` of :func:`tuple`
    """
    categories = []
    counts = []
    for item in items:
        if item in categories:
            idx = categories.index(item)
            counts[idx] = counts[idx] + 1
        else:
            categories.append(item)
            counts.append(1)
    return zip(categories, counts)
