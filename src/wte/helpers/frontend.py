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
import re

from genshi.builder import tag, Markup
from pywebtools import text

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


def page_pagination(request, part):
    """Generates the pagination UI for the individual page display of a
    :class:`~wte.models.Part`.

    :param request: The current request
    :type request: :class:`~pyramid.request.Request`
    :param part: The current parte to display pagination for
    :type part: :class:`~wte.models.Part`
    :return: The resulting HTML markup
    """
    prev_page = None
    next_page = None
    state = 0
    for child in part.parent.children:
        if state == 0 and child != part:
            prev_page = child
        elif state == 0 and child == part:
            state = 1
        elif state == 1:
            next_page = child
            break
    if prev_page:
        prev_page = tag.a(tag.span(class_='fi-previous icon'),
                          title='Previous page (%s)' % (prev_page.title),
                          href=request.route_url('part.view', pid=prev_page.id))
    else:
        prev_page = tag.span(class_='fi-previous icon unavailable')
    prev_page = tag.div(prev_page,
                        class_='small-6 large-2 column text-center')
    if next_page:
        next_page = tag.a(tag.span(class_='fi-next icon'),
                          title='Next page (%s)' % (next_page.title),
                          href=request.route_url('part.view', pid=next_page.id))
    else:
        next_page = tag.span(class_='fi-next icon unavailable')
    next_page = tag.div(next_page,
                        class_='small-6 large-2 column text-center')
    page_jump = tag.form(tag.select([tag.option(p.title,
                                                value=p.id,
                                                selected='selected' if p.id == part.id else None)
                                     for p in part.parent.children]),
                         action=request.route_url('part.view', pid='pid'),
                         class_='show-for-large-up large-8 column')
    min_progress = max(0, int(100.0 * (part.order) / len(part.parent.children)))
    max_progress = min(100, int(100.0 * (part.order + 1) / len(part.parent.children)))
    return tag.nav(tag.div(tag.div(tag.div(prev_page, page_jump, next_page,
                                           class_='row collapse'),
                                   tag.div(tag.span(class_='meter',
                                                    style='width:%i%%;' % (min_progress)),
                                           class_='progress',
                                           title='Page %i of %i' % (part.order + 1, len(part.parent.children))),
                                   class_='pagination',
                                   data_progress='%s' % (json.dumps({'min': min_progress, 'max': max_progress}))),
                           class_='small-12 column'),
                   class_='row collapse')


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


def part_summary(part):
    """Generates summary text for a :class:`~wte.models.Part` by extracting the first HTML element
    from the ``compiled_content``. Due to the use of ReST, this should in most cases be the first
    paragraph.

    :param part: The :class:`~wte.models.Part` to generate the summary for
    :type part: :class:`~wte.models.Part`
    :return: The first HTML element
    :rtype: :class:`~genshi.builder.Markup`
    """
    content = part.compiled_content
    if content:
        m = re.search(r'<([a-zA-Z+])>', content)
        if m:
            start = content.find('<%s>' % (m.group(1)))
            end = content.find('</%s>' % (m.group(1))) + len(m.group(1)) + 3
            return Markup(content[start:end])
    return None


def menubar(menu, drop_down_menu_left=True, class_=None):
    """Generates a menu bar for a nested set of menu groups and menu items. Each menu group is specified as
    a ``dict`` with the following keys:

    * *group*: the name of the group
    * *items*: a list of menu item ``dict``

    Each menu item is specified as a ``dict``, which has the following keys:

    * *visible*: whether the element is displayed (``True``/``False``)
    * *label*: the label text to show
    * *href*: the href for the menu link
    * *class*: the CSS class to specify on the menu link [optional]
    * *icon*: a foundation icon to show for the menu link [optional]
    * *confirm*: confirmation text to show before the link is followed [optional]
    * *highlight*: whether to also show the item at the top-level of the menubar (``True``/``False``) [optional]

    Menu items that are marked as 'highlight: ``True`` and have an 'icon' set, will be shown at the top level of
    the menubar. All other items are shown in a drop-down menu.

    :param menu: The list of menu groups and items
    :type menu: ``list``
    :param drop_down_menu_left: Whether the drop-down menus should be left (True) or right-aligned (False)
    :type drop_down_menu_left: ``bool``
    :param class_: Additional CSS classes to add to the main menubar element
    :type class_: ``unicode``
    :return: The generated HTML elements
    :rtype: :class:`~genshi.builder.tag`"""
    full_menu = []
    highlight = []
    for group in menu:
        if(len(full_menu) > 0):
            full_menu.append(tag.li(class_='divider'))
        for item in group['items']:
            if item['visible']:
                full_menu.append(tag.li(tag.a(item['label'],
                                              href=item['href'],
                                              class_=item['class'] if 'class' in item else None,
                                              data_wte_confirm=item['confirm'] if 'confirm' in item else None,
                                              target=item['target'] if 'target' in item else None)))
                if 'highlight' in item and item['highlight'] and 'icon' in item:
                    item['group'] = group['group']
                    highlight.append(item)
    groups = []
    group = None
    for item in highlight:
        if group != item['group']:
            groups.append([])
            group = item['group']
        groups[len(groups) - 1].append(item)
    items = []
    for group in groups:
        if len(group) == 1:
            item = group[0]
            items.append(tag.li(tag.a(tag.span(class_=item['icon'],
                                               aria_hidden='true'),
                                      tag.span(group[0]['label'],
                                               class_='show-for-sr'),
                                      title=group[0]['label'],
                                      href=item['href'],
                                      class_=item['class'] if 'class' in item else None,
                                      data_wte_confirm=item['confirm'] if 'confirm' in item else None,
                                      target=item['target'] if 'target' in item else None)))
        else:
            sub_menu = []
            for item in group:
                sub_menu.append(tag.li(tag.a(item['label'],
                                             href=item['href'],
                                             class_=item['class'] if 'class' in item else None,
                                             data_wte_confirm=item['confirm'] if 'confirm' in item else None,
                                             target=item['target'] if 'target' in item else None)))
            items.append(tag.li(tag.div(tag.a(tag.span(class_=group[0]['icon'],
                                                       aria_hidden='true'),
                                              tag.span(text.title(group[0]['group']),
                                                       class_='show-for-sr'),
                                              href='#'),
                                        tag.ul(sub_menu),
                                        class_='menu',
                                        data_wte_menu_position='left' if drop_down_menu_left else 'right')))
    items.append(tag.li(tag.div(tag.a(tag.span(class_='fi-list',
                                               aria_hidden='true'),
                                      tag.span('Actions',
                                               class_='show-for-sr'),
                                      href='#',
                                      title='All actions'),
                                tag.ul(full_menu),
                                class_='menu',
                                data_wte_menu_position='left' if drop_down_menu_left else 'right')))
    return tag.ul(items, class_='menubar %s' % (class_) if class_ else 'menubar')


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
