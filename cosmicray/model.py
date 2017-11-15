# -*- coding: utf-8 -*-


class Model(object):

    __fields__ = []
    __ignorefields__ = []
    __route__ = None

    def __init__(self, **kwargs):
        self.setfields(**kwargs)
        self.changes = []

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        self.track_changes(name)

    def setfields(self, **fields):
        for field in self.__fields__:
            setattr(self, field, fields.pop(field, None))
        for field in self.__ignorefields__:
            fields.pop(field, None)
        if fields:
            print('{!r} got extra fields: {}'.format(
                self.__class__.__name__, ', '.join(fields.keys())))

    def items(self):
        return [(field, getattr(self, field)) for field in self.__fields__]

    def get_dict(self):
        return dict((k, v) for k, v in self.items())

    def set_dict(self, fields):
        self.setfields(**fields)

    dict = property(get_dict, set_dict)

    def __nonzero__(self):
        return any(value is not None for _, value in self.items())

    def track_changes(self, field):
        changes = self.__dict__.get('changes')
        if changes and field in self.__fields__:
            self.changes.append(name)

    def clear_changes(self):
        self.changes = []

    def create_payload(self):
        return {'json': self.dict}

    def update_payload(self):
        return {'json': self.dict}

    def set_params(self, from_dict_obj=None, **kwargs):
        return self.get_route().set_params(from_dict_obj, **kwargs)

    def set_urlargs(self, from_dict_obj=None, **kwargs):
        return self.get_route().set_urlargs(from_dict_obj, **kwargs)

    def get_route(self):
        return self.__route__(
            model_cls=self.__class__, urlargs=self.dict)

    def get(self):
        return self.get_route().get()

    def delete(self):
        return self.get_route().delete()

    def create(self):
        return self.get_route().set_payload(**self.create_payload()).post()

    def update(self):
        return self.get_route().set_payload(**self.update_payload()).put()

    @classmethod
    def _make(cls, fields):
        return cls(**fields)

    def __repr__(self):
        changed = ' has pending updates' if self.changes else ''
        fields = ', '.join('{}={!r}'.format(f, v) for f, v in self.items())
        return '<{model}({fields}){changed}>'.format(
            model=self.__class__.__name__, fields=fields, changed=changed)
