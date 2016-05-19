# -*- coding: utf-8 -*-
"""
####################################
:mod:`wte.util` -- Utility functions
####################################

The :mod:`~wte.util` module provides various utility objects and
functions.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import asset
import logging
import math
import smtplib

from email.mime.text import MIMEText
from email.utils import formatdate
from pyramid.httpexceptions import HTTPSeeOther
from pywebtools.pyramid.util import get_config_setting


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
    """Sends an e-mail based on the settings in the configuration file. If
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
            logging.getLogger("wte").error(str(e))
            print(text)  # TODO: Remove
    else:
        logging.getLogger("wte").error('Could not send e-mail as "email.smtp_host" setting not specified')
        print(text)  # TODO: Remove


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
                          'label': str(idx + 1)})
        else:
            pages.append({'type': 'item',
                          'label': str(idx + 1),
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
    return list(zip(categories, counts))
