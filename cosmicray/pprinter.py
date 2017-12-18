# -*- coding: utf-8 -*-
import operator

import six


LIST = '`-- '
INDENT = ' ' * (len(LIST))
INDENT_LEVEL = 1


class ModelPPrinter(object):
    '''
    Pretty Print model and it's attributes
    '''
    ROW_FORMATTER = '{{indent}}{list_type}{name}{attr}{end}'

    def __init__(self, model, attributes, formatters, **kwargs):
        self.model = model
        self.attributes = [attr for attr in attributes if attr not in formatters]
        self.formatters = formatters
        self.args = kwargs
        self.writer = six.StringIO()

    def get_formatter(self, attr=None, name=None, list_type='', end='\n'):
        attr = '{{0.{attr}}}'.format(attr=attr) if attr else '{value}'
        return self.ROW_FORMATTER.format(
            name=name or '',
            attr=attr, list_type=list_type, end=end)

    def get_attribute_formatter(self, attributes, list_type=LIST, end='\n'):
        return ''.join(
            self.get_formatter(attr, '{}: '.format(attr) if attr else '',
                               list_type, end) for attr in attributes)

    def get_indent(self, level):
        return INDENT * (INDENT_LEVEL * level)

    def get_attr(self, model, attr):
        return operator.attrgetter(attr)(model)

    def pprint(self, max_depth=3):
        self._write(self.get_formatter(self.attributes.pop(0)), self.model, indent='')
        self._write(self.get_attribute_formatter(self.attributes), self.model, indent='')

        for attr, formatter in self.formatters.items():
            name = formatter.get('name', attr)
            row_formatter = self.get_formatter(name=name, list_type=LIST)
            value = formatter['formatter'].format(self.get_attr(self.model, attr))
            self._write(row_formatter, name=name, value=value, indent='')

        for child_attr, child_meta in self.args.items():
            children = getattr(self.model, child_attr)
            key = child_meta.get('filter')
            recursive = child_meta.get('recursive')
            formatters = child_meta.get('formatters', {})
            attributes = child_meta['attributes']
            hformatter = self.get_formatter(attributes.pop(0), list_type=LIST)
            rformatter = self.get_attribute_formatter(attributes) if attributes else ''
            for child in self._filter(self.model, children, key):
                self.writer.write(hformatter.format(child, indent=''))
                self.writer.write(rformatter.format(child, indent=self.get_indent(1)))
                if recursive:
                    self._pprint_children(
                        child, children, 1, key, hformatter, rformatter)
        print(self.writer.getvalue())

    def _pprint_children(self, parent, children, level, key, hformatter, rformatter):
        for child in self._filter(parent, children, key):
            self._write(hformatter, child, indent=self.get_indent(level))
            self._write(rformatter, child, indent=self.get_indent(level + 1))
            self._pprint_children(child, children, level + 1, key, hformatter, rformatter)

    def _filter(self, parent, children, key):
        if not key:
            return children
        return (c for c in children if key(parent, c))

    def _write(self, formatter, *args, **kwargs):
        self.writer.write(formatter.format(*args, **kwargs))


def pprint(model, attributes, formatters, **kwargs):
    ModelPPrinter(
        model, attributes, formatters or {}, **kwargs).pprint()
