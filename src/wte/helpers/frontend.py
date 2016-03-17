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

from wte.util import get_config_setting

inflector = inflect.engine()


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


class MenuBuilder(object):
    """The :class:`~wte.helpers.frontend.MenuBuilder` helps with creating the ``list``
    structure used for creating the icon-menubar. Call :func:`~wte.helpers.frontend.MenuBuilder.group`
    to start a new group of menu items. Call :func:`~wte.helpers.frontend.MenuBuilder.item`
    to add a menu item to the current group. :func:`~wte.helpers.frontend.MenuBuilder.generate`
    then generates the final structure for use in the menubar.
    """

    def __init__(self):
        self._groups = []
        self._group = None

    def group(self, label, icon=None):
        """Add a new group to the lost of groups in this :class:`~wte.helpers.frontend.MenuBuilder`.

        :param label: The menu group's label
        :type label: `unicode`
        :param icon: The optional icon for this group. An icon must be provided in order to
                     enable highlighting of menu items
        :type icon: `unicode`
        """
        if self._group and self._group['items']:
            self._groups.append(self._group)
        self._group = {'label': label,
                       'items': []}
        if icon:
            self._group['icon'] = icon

    def menu(self, label, href, icon=None, highlight=False, attrs=None):
        """Add a new menu item to the current group. Will create a new group with an empty
        label if :func:`~wte.helpers.frontend.MenuBuilder.group` has not been called

        :param label: The menu item's label
        :type label: `unicode`
        :param href: The URL that the menu item loads
        :type href: `unicode`
        :param icon: The optional icon for this menu item
        :type icon: `unicode`
        :param highlight: Whether to highlight the menu item by displaying it at the top level
        :type highlight: `boolean`
        :param attrs: Additional attributes to set for the menu item link
        :type attrs: :py:`dict`
        """
        if not self._group:
            self._group = {'label': '',
                           'items': []}
        if attrs:
            attrs['href'] = href
        else:
            attrs = {'href': href}
        item = {'visible': True,
                'label': label,
                'attrs': attrs}
        if icon:
            item['icon'] = icon
        if highlight:
            item['highlight'] = True
        self._group['items'].append(item)

    def generate(self):
        """Generate the final menu structure.

        :return: The list of menu groups with their menu items
        :r_type: ``list`` of menu groups
        """
        if self._group and self._group['items']:
            self._groups.append(self._group)
            self._group = None
        return self._groups


def readable_timedelta(delta):
    """Converts a :class:`datetime.timedelta` into a human-readable string.

    :param delta: The time-delta to convert
    :type delta: :class:`datetime.timedelta`
    :return: The human-readable string representation of the ``delta``
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
