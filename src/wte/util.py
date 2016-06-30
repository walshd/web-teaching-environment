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
