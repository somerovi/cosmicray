# -*- coding: utf-8 -*-
import collections
import operator

import colorama
import six


MAX_DEPTH = 10
TAB_WIDTH = 4
TAB = ' '
LIST_ITEM = '└─► '
COLOR_OUTPUT = True
BOLD = colorama.Style.BRIGHT
DIM = colorama.Style.DIM
NORMAL = colorama.Style.NORMAL
FG_BLACK = colorama.Fore.BLACK
FG_RED = colorama.Fore.RED
FG_GREEN = colorama.Fore.GREEN
FG_YELLOW = colorama.Fore.YELLOW
FG_BLUE = colorama.Fore.BLUE
FG_MAGENTA = colorama.Fore.MAGENTA
FG_CYAN = colorama.Fore.CYAN
FG_WHITE = colorama.Fore.WHITE
FG_NORMAL = colorama.Fore.RESET
BG_BLACK = colorama.Back.BLACK
BG_RED = colorama.Back.RED
BG_GREEN = colorama.Back.GREEN
BG_YELLOW = colorama.Back.YELLOW
BG_BLUE = colorama.Back.BLUE
BG_MAGENTA = colorama.Back.MAGENTA
BG_CYAN = colorama.Back.CYAN
BG_WHITE = colorama.Back.WHITE
BG_NORMAL = colorama.Back.RESET


def colored(fore, back, style):
    '''Formats the given colors and style into a string object'''
    return '%s%s%s' % (style, fore, back)


def formatter(list_item, color_output=COLOR_OUTPUT):
    '''Creates a string formatter for the given list item style'''
    color = '{color}' if color_output else ''
    color_reset = colorama.Style.RESET_ALL if color_output else ''
    return '{indent}%s%s{}%s\n' % (list_item, color, color_reset)


def get_attr(obj, attr):
    '''
    Gets the attribute value for the given attribute name and object.
    Allows nested attribute notation: attr.attr2
    :param obj: Object
    :param attr: String attribute name.
    :return value
    '''
    return operator.attrgetter(attr)(obj)


def rfilter(key, parent, sequence):
    '''
    :param key: callable, must accept two arguments, parent and child
    :param parent: Previous element from the sequence
    :param sequence: Iterable object
    '''
    if not key:
        return sequence
    return (c for c in sequence if key(parent, c))


def pprint(model, formattings, level=0):
    '''
    Pretty print the model with the given formatting parameters
    :param model: ``cosmicray.mode.Model`` object
    :param formattings: List of ``Formatting`` objects
    :param level: Indentation level. Default: 0

    Usage::
        class Dog(cosmicray.model.Model):
            __slots__ = ['id', 'name', 'breed']
            friends = cosmicray.model.relationship('Friend',
                urlargs={'id': cosmicray.model.ModelParam('id')}))
            owner = cosmicray.model.relationship('Owner',
                urlargs={'id': cosmicray.model.ModelParam('id')}))
            ...

        class Friend(cosmicray.model.Model):
            __slots__ = ['id', 'name', 'friendType', 'friendId']
            ...

        class Owner(cosmicray.model.Model):
            __slots__ = ['id', 'name']
            ...

        dog = Dog(id=12345).get()
        pprint(dog, formattings=[
            # Format header
            Formatting(formatter='{0.name} > {0.id}', color=FG_RED),
            # Format owners name
            Formatting('owner.name', color=FG_GREEN),
            # Format friends in hierarchical manner
            Formatting('friends',
                formatter='{0.name} > {0.id}',
                color=pprint.colored(pprint.FG_BLUE, pprint.BG_NORMAL, pprint.BOLD),
                is_recursive=True,
                is_sequence=True,
                rfilter=lambda parent, child: (
                    child.friendId == parent.id and child.friendType == (
                        'DOG' if isinstance(parent, Dog)
                        else 'FRIEND'))),
        ])
    '''
    colorama.init()
    pprinter = PrettyPrinter(TAB, TAB_WIDTH)
    pprinter.pprint(model, formattings, level)
    print(pprinter)


class Formatting(object):
    '''
    :param attr_name: A models attribute name. Optional.
    :param formatter: Formatting string using new style pythong formatting language.
        If ``attr_name`` is given formats the attributes value, otherwise formats the given model
    :param is_sequence: True|False. Indicates if attributes value is of type sequence. Default: False
    :param is_recursive: True|False. Used in conjunction with ``is_sequence`` and ``rfilter``.
        Indicates the given items in the sequence have a recursive relationship
    :param rfilter: Callable that must accept two arguments: parent and current, where parent
        is either a previous item from the sequence, or the model passed in to pprint
        Default: None
    :param color: Terminal color codes
    :param formattings: List of ``Formatting`` objects
    '''
    def __init__(self, attr_name=None, formatter=None, is_sequence=False,
                 is_recursive=False, rfilter=None, color=None, color_if=None,
                 formattings=None):
        self.attr_name = attr_name
        self.formatter = formatter
        self.is_sequence=is_sequence
        self.is_recursive = is_recursive
        self.rfilter = rfilter
        self.formattings = formattings or []
        self.color = color
        self.color_if = color_if

    def get_color(self, obj):
        if self.color_if:
            return self.color_if(obj)
        elif self.color:
            return self.color
        return ''


class PrettyPrinter(object):
    def __init__(self, tab, tab_width):
        self.writer = six.StringIO()
        self.formatter = formatter(list_item=LIST_ITEM)
        self.is_first = True
        self.tabs = tab * tab_width

    def write(self, obj):
        self.writer.write(obj)

    def writerow(self, obj, formatting, level, no_formatting=False):
        value = obj
        if formatting.formatter and not no_formatting:
            value = formatting.formatter.format(obj)
        color = formatting.get_color(value)
        if self.is_first and level == 0:
            self.write(formatter(list_item='').format(
                value, indent='', color=color))
            self.is_first = False
        else:
            self.write(
                self.formatter.format(
                    value, indent=(self.tabs * level), color=color))

    def __str__(self):
        return self.writer.getvalue()

    def rpprint(self, parent, sequence, formatting, level):
        if level >= MAX_DEPTH:
            return
        for item in rfilter(formatting.rfilter, parent, sequence):
            if formatting.formatter:
                self.writerow(item, formatting, level)
            if formatting.formattings:
                self.pprint(item, formatting.formattings, level + 1)
            if formatting.is_recursive:
                self.rpprint(item, sequence, formatting, level + 1)

    def pprint(self, model, formattings, level):
        if level >= MAX_DEPTH:
            return
        for formatting in formattings:
            increment = 0 if self.is_first else 1
            if formatting.attr_name:
                attr_value = get_attr(model, formatting.attr_name)
                if formatting.is_sequence:
                    self.writerow(formatting.attr_name, formatting, level, no_formatting=True)
                    self.rpprint(model, attr_value, formatting, level + increment)
                else:
                    self.writerow(attr_value, formatting, level)
            else:
                if formatting.is_sequence:
                    self.writerow(model.__class__.__name__,
                                  formatting, level, no_formatting=True)
                    self.rpprint(None, model, formatting, level)
                else:
                    self.writerow(model, formatting, level)
                    if formatting.formattings:
                        self.pprint(model, formatting.formattings, level)
