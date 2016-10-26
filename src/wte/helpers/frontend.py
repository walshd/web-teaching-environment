# -*- coding: utf-8 -*-
"""
###############################################################
:mod:`wte.helpers.frontend` -- Helpers for the frontend display
###############################################################

The :mod:`~wte.helpers.frontend` module provides helper functionality used to
render the frontend page displays.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import inflect
import json
import math

from pywebtools.pyramid.util import (get_config_setting, MenuBuilder)

inflector = inflect.engine()


def lt(a, b):
    """Helper function that checks if ``a`` is less than ``b``.
    """
    return a < b


def html_id(text):
    """Turns a given text into a valid HTML id attribute value. Removes
    spaces and full-stops.

    :param text: The text to convert
    :type text: `unicode`
    :return: The corresponding HTML id
    :rtype: :func:`unicode`
    """
    return text.replace(' ', '_').replace('.', '_')


CODEMIRROR_MODES = {'text/html': ['javascript',
                                  'css',
                                  'xml',
                                  'htmlmixed',
                                  ('../addon/fold/', 'xml-fold'),
                                  ('../addon/edit', 'matchtags')],
                    'text/css': ['css',
                                 ('../addon/edit', 'matchbrackets'),
                                 ('../addon/lint', 'lint'),
                                 ('../addon/lint', 'csslint'),
                                 ('../addon/lint', 'css-lint')],
                    'text/javascript': ['javascript',
                                        ('../addon/edit', 'matchbrackets'),
                                        ('../addon/lint', 'lint'),
                                        ('../addon/lint', 'jshint'),
                                        ('../addon/lint', 'javascript-lint')],
                    'application/javascript': ['javascript',
                                               ('../addon/edit', 'matchbrackets'),
                                               ('../addon/lint', 'lint'),
                                               ('../addon/lint', 'jshint'),
                                               ('../addon/lint', 'javascript-lint')],
                    'text/x-rst': ['python',
                                   'stex',
                                   ('../addon/mode', 'overlay'),
                                   'rst']}


def codemirror_scripts(request, mimetypes):
    """Generates the ``<script>`` tags necessary to load the CodeMirror mode
    JS files for the given list of ``mimetypes``.

    :param request: The request to use for generating URLs
    :type request: `~pyramid.request.Request`
    :param mimetypes: The mimetypes to load the CodeMirror modes for
    :type mimetypes: `list` of `unicode`
    :return: The necessary ``<script>`` tags
    """
    modes = []
    for mimetype in mimetypes:
        if mimetype in CODEMIRROR_MODES:
            for mode in CODEMIRROR_MODES[mimetype]:
                if isinstance(mode, tuple):
                    modes.append(mode)
                else:
                    modes.append((mode, mode))
    scripts = [request.static_url('wte:static/js/codemirror/codemirror.js')]
    for mode in modes:
        script = request.static_url('wte:static/js/codemirror/mode/%s/%s.js' % mode)
        if script not in scripts:
            scripts.append(script)
    return scripts


CODEMIRROR_OPTIONS = {'text/html': {'matchTags': True},
                      'text/css': {'gutters': ['CodeMirror-lint-markers'],
                                   'matchBrackets': True,
                                   'lint': True},
                      'text/javascript': {'lint': True,
                                          'gutters': ['CodeMirror-lint-markers'],
                                          'matchBrackets': True},
                      'application/javascript': {'gutters': ['CodeMirror-lint-markers'],
                                                 'matchBrackets': True,
                                                 'lint': True}}


def codemirror_options(request, mimetype, include_mode=False):
    """Generates a JSON representation of CodeMirror options that are valid
    for the given ``mimetype``.

    :param request: The current request
    :type request: :class:`~pyramid.request.Request`
    :param mimetype: The mimetype to generate CodeMirror options for
    :type mimetype: `unicode`
    :param include_mode: Whether to include the ``mode`` setting in the options
    :type include_mode: `bool`
    :return: The JSON representation of options
    """
    options = {'theme': get_config_setting(request, 'codemirror.theme', default='default')}
    if include_mode:
        options['mode'] = mimetype
    if mimetype in CODEMIRROR_OPTIONS:
        options.update(CODEMIRROR_OPTIONS[mimetype])
    return json.dumps(options)


def confirm_action(title, message, cancel, ok):
    """Generates a confirmation JSON object for use with the jQuery.postLink() plugin.

    :param title: The title of the confirmation dialog box
    :type title: ``unicode``
    :param message: The main message to show
    :type message: ``unicode``
    :param cancel: The cancel button's settings
    :type cancel: ``dict`` or ``unicode``
    :param ok: The ok button's settings
    :type ok: ``dict`` or ``unicode``
    :return: JSON object
    :rtype: :func:`unicode`
    """
    return json.dumps({'title': title,
                       'msg': message,
                       'cancel': cancel if isinstance(cancel, dict) else {'label': cancel},
                       'ok': ok if isinstance(ok, dict) else {'label': ok}})


def confirm_delete(obj_type, title, has_parts=False):
    """Generates the confirmation JSON object for use with the jQuery.postLink() plugin.

    :param obj_type: The type of object that is being deleted
    :type obj_type: ``unicode``
    :param title: The title of the object that is being delete
    :type title: ``unicode``
    :param has_parts: Whether to add the suffix " and all its parts"
    :type has_parts: ``bool``
    :return: JSON object
    :rtype: :func:`unicode`
    """
    msg = 'Please confirm that you wish to delete the %s "%s"' % (obj_type, title)
    if has_parts:
        msg = '%s and all its parts.' % (msg)
    else:
        msg = '%s.' % (msg)
    return confirm_action('Delete this %s' % (obj_type),
                          msg,
                          "Don't delete",
                          {'label': 'Delete',
                           'class_': 'alert'})


def time_string(days, hours, minutes, seconds):
    """Converts the ``days``, ``hours``, ``minutes``, and ``seconds`` into
    a human-readable format.

    :param days: The number of days to the timestamp
    :type days: :func:`int`
    :param hours: The number of hours to the timestamp
    :type hours: :func:`int`
    :param minutes: The number of minutes to the timestamp
    :type minutes: :func:`int`
    :param seconds: The number of seconds to the timestamp
    :type seconds: :func:`int`
    :return: The human-readable representation
    :rtype: :func:`unicode`
    """
    def number_unit(number, unit, fraction=None):
        """Formats a string "number unit", where the unit is appropriately
        pluralised. Optionally the parameter ``fraction`` can be inserted
        between the two.

        :param number: The number to return
        :type number: :func:`int`
        :param unit: The unit to return with the number (singular)
        :type unit: :func:`unicode`
        :param fraction: The fraction to insert between number and unit
        :type fraction: :func:`unicode`
        :return: The string "number unit" or "number fraction unit"
        :rtype: :func:`unicode`
        """
        if fraction is not None:
            return '%i %s %s' % (number, fraction, inflector.plural(unit, number))
        else:
            return '%i %s' % (number, inflector.plural(unit, number))

    if days > 60:
        return 'about %s' % number_unit(math.ceil(days / 30.0), 'month')
    elif days > 14:
        return 'about %s' % number_unit(math.ceil(days / 7.0), 'week')
    elif days > 5:
        if hours > 16:
            return 'a bit less than %s' % number_unit(days + 1, 'day')
        elif hours > 8:
            return 'about %s' % number_unit(days, 'day', fraction='and a half')
        else:
            return 'about %s' % number_unit(days, 'day')
    elif days > 0:
        if hours > 0:
            return '%s and %s' % (number_unit(days, 'day'), number_unit(hours, 'hour'))
        else:
            return number_unit(days, 'day')
    elif hours > 6:
        if minutes > 50:
            return 'a bit less than %s' % number_unit(hours + 1, 'hour')
        elif minutes > 20:
            return number_unit(hours, 'hour', fraction='and a half')
        else:
            return number_unit(hours, 'hour')
    elif hours > 0:
        if minutes > 0:
            if seconds > 0:
                return '%s and %s' % (number_unit(hours, 'hour'), number_unit(minutes + 1, 'minute'))
            else:
                return '%s and %s' % (number_unit(hours, 'hour'), number_unit(minutes, 'minute'))
        else:
            return number_unit(hours, 'hour')
    elif minutes > 0:
        if seconds > 0:
            return number_unit(minutes + 1, 'minute')
        else:
            return number_unit(minutes, 'minute')
    elif seconds > 30:
        return 'less than a minute'
    elif seconds > 15:
        return 'less than 30 seconds'
    else:
        return number_unit(seconds, 'second')


def readable_timedelta(delta):
    """Converts a :class:`datetime.timedelta` into a human-readable string.

    :param delta: The time-delta to convert
    :type delta: :class:`datetime.timedelta`
    :return: The human-readable string representation of the ``delta``
    :rtype: :func:`unicode`
    """
    if delta.days < 0:
        delta = abs(delta)
        return '%s ago' % time_string(delta.days,
                                      int(math.floor(delta.seconds / 3600)),
                                      int(math.floor((delta.seconds % 3600) / 60)),
                                      int(math.floor((delta.seconds % 3600) % 60)))
    else:
        return 'in %s' % time_string(delta.days,
                                     int(math.floor(delta.seconds / 3600)),
                                     int(math.floor((delta.seconds % 3600) / 60)),
                                     int(math.floor((delta.seconds % 3600) % 60)))


DISPLAY_MODES = {'default': {'module': '_module.html',
                             'tutorial': '_tutorial.html',
                             'exercise': '_exercise.html'},
                 'three_pane_html': {'page': '_page.html',
                                     'task': '_task.html'},
                 'text_only': {'page': '_page.html',
                               'task': '_task.html'}}


def split_seconds(seconds):
    """Converts a time in seconds into a ``(days, hours, minutes, seconds)``
    tuple for use in :func:`~wte.helpers.frontend.time_string`.

    :param seconds: The time in seconds to split
    :type seconds: ``int``
    :return: A tuple ``(days, hours, minutes, seconds)``
    :rtype: ``tuple``
    """
    days = math.floor(seconds / (3600 * 24))
    seconds = seconds % (3600 * 24)
    hours = math.floor(seconds / 3600)
    seconds = seconds % 3600
    minutes = math.floor(seconds / 60)
    seconds = seconds % 60
    return (days, hours, minutes, seconds)


def template_for_part(part):
    """Returns the correct partial template path for a given
    :class:`~wte.models.Part`. If there is no partial template for the given
    :class:`~wte.models.Part`, then ``None`` is returned.

    :param part: The :class:`~wte.models.Part` to generate the template path for
    :type part: :class:`~wte.models.Part`
    :return: The partial template path or ``None``
    :return_type: ``string``
    """
    part_type = part.type
    display_mode = part.display_mode
    if display_mode == 'inherit':
        display_mode = part.parent.display_mode
    if display_mode in DISPLAY_MODES and part_type in DISPLAY_MODES[display_mode]:
        return '%s/%s' % (display_mode, DISPLAY_MODES[display_mode][part_type])
    elif part_type in DISPLAY_MODES['default']:
        return 'default/%s' % (DISPLAY_MODES['default'][part_type])
    return None


def natural_list(items, separator=', ', final_separator=' & '):
    """Returns a string representation of the ``items`` list. For an empty list
    or a single item the value is returned. For a list of two items, the items
    are joined together using the ``final_separator``. For a list of more than
    two items, the all but the last item are joined using ``separator`` and the
    last item is joined using ``final_separator``.

    :param items: The list of items to join
    :type items: :func:`list`
    :param separator: The separator to use when more than 2 items are joined.
                      Defaults to ', '.
    :type separator: :func:`unicode`
    :param final_separator: The separator to use for the last two items in the list.
                            Defaults to ' & '.
    :type separator: :func:`unicode`
    :return: A string representation of the list
    :return_type: :func:`unicode`
    """
    if len(items) == 0:
        return ''
    if len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return final_separator.join(items)
    else:
        return '%s %s %s' % (separator.join(items[:-1]), final_separator, items[-1])


def set_list(items):
    """Returns a string representation of the unique items in the ``items``. The
    ``items`` must be a :func:`list` of :func:`tuple` ``(item, count)`` as returned
    by :func:`~wte.util.ordered_counted_set`.

    :param items: The list of items to transform into a string
    :type istems: :func:`list` of :func:`tuple`
    :return: A string containing all unique items
    :return_type: :func:`unicode`
    """
    return natural_list([inflector.plural(category, count) for (category, count) in items])


def user_admin_menubar(request, user):
    """Generates the menu bar for the users administration list."""
    builder = MenuBuilder()
    if user.allow('edit', request.current_user):
        if user.status == 'active':
            builder.group('Edit', 'fi-pencil')
            builder.menu('Edit',
                         request.route_url('user.edit', uid=user.id),
                         icon='fi-pencil',
                         highlight=True)
            builder.group('Access', 'fi-key')
            builder.menu('Edit Permissions',
                         request.route_url('user.permissions', uid=user.id),
                         icon='fi-key',
                         highlight=True)
            builder.menu('Reset Password',
                         request.route_url('user.forgotten_password',
                                           _query=[('email', user.email),
                                                   ('csrf_token', request.session.get_csrf_token()),
                                                   ('return_to', request.current_route_url())]),
                         attrs={'class': 'post-link'})
        else:
            builder.group('Access', 'fi-key')
            builder.menu('Validate user',
                         request.route_url('users.action', _query=[('user_id', user.id),
                                                                   ('action', 'validate'),
                                                                   ('csrf_token', request.session.get_csrf_token())]),
                         icon='fi-check',
                         highlight=True,
                         attrs={'class': 'post-link'})
    if user.allow('delete', request.current_user):
        builder.group('Delete', 'fi-trash')
        builder.menu('Delete',
                     request.route_url('user.delete',
                                       uid=user.id,
                                       _query={'csrf_token': request.session.get_csrf_token()}),
                     icon='fi-trash',
                     attrs={'class': 'alert post-link',
                            'data-wte-confirm': confirm_delete('user', user.display_name, False)})
    return builder.generate()


def part_change_notification_text(request, part):
    """Generates a default notification text to be emailed when changes
    are made to a part.

    :param request: The current request to get the current user from
    :type request: :class:`~pyramid.request.Request`
    :param part: The part that is being changed
    :type part: :class:`~wte.models.Part`
    :return: The default notification text
    :rtype: ``str``
    """
    if part.type == 'module':
        return '''Hello,

This is to let you know that changes have been made to the %s module.

Please reload the module to see the changes.

%s''' % (part.title,
         request.current_user.display_name)
    elif part.type == 'part':
        return '''Hello,

This is to let you know that changes have been made to the %s %s of the %s module.

Please reload the %s to see the changes.

%s''' % (part.title,
         part.label if part.label else 'part',
         part.parent.title,
         part.label if part.label else 'part',
         request.current_user.display_name)
    elif part.type == 'page':
        return '''Hello,

This is to let you know that changes have been made to the page "%s" in the %s %s of the %s module.

Please reload that page to see the changes.

%s''' % (part.title,
         part.parent.title,
         part.parent.label if part.parent.label else 'part',
         part.parent.parent.title,
         request.current_user.display_name)
