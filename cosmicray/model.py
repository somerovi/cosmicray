# -*- coding: utf-8 -*-


class Model(object):

    __fields__ = []
    __ignorefields__ = []
    __route__ = None

    def __init__(self, **kwargs):
        self._setfields(**kwargs)
        self.changes = []

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        self._track_changes(name)

    def _setfields(self, **fields):
        for field in self.__fields__:
            setattr(self, field, fields.pop(field, None))
        for field in self.__ignorefields__:
            fields.pop(field, None)
        if fields:
            print('{!r} got extra fields: {}'.format(
                self.__class__.__name__, ', '.join(fields.keys())))

    def items(self):
        '''Returns iterator of key-value pairs from the objects fields'''
        return ((field, getattr(self, field)) for field in self.__fields__)

    def get_dict(self):
        '''Returns dict representation of the object'''
        return dict((k, v) for k, v in self.items())

    def set_dict(self, fields):
        '''Updates fields from the given dict object'''
        updates = self.get_dict()
        updates.update(fields)
        self._setfields(**updates)

    dict = property(get_dict, set_dict, doc='Getter and setter from dict object')

    def __nonzero__(self):
        return any(value is not None for _, value in self.items())

    def _track_changes(self, field):
        changes = self.__dict__.get('changes')
        if changes and field in self.__fields__:
            self.changes.append(name)

    def _clear_changes(self):
        self.changes = []

    def create_payload(self):
        '''POST request default payload: { "json" : self.dict }'''
        return {'json': self.dict}

    def update_payload(self):
        '''PUT request default payload: { "json" : self.dict }'''
        return {'json': self.dict}

    def get_request(self, **kwargs):
        '''Returns :class:`cosmicray.Request` with :class:`Model`.__class__ as the model_cls
        and ``self.dict`` as urlargs'''
        return self.__route__(
            model_cls=self.__class__, urlargs=self.dict, **kwargs)

    def get(self):
        '''GET request'''
        return self.get_request().get()

    def delete(self):
        '''DELETE request'''
        return self.get_request().delete()

    def create(self):
        '''POST request. Uses :class:`Model.create_payload` as the POST body'''
        return self.get_request(**self.create_payload()).post()

    def update(self):
        '''PUT request. Uses :class:`Model.update_payload` as the PUT body'''
        return self.get_request(**self.update_payload()).put()

    @classmethod
    def _make(cls, fields):
        return cls(**fields)

    def __repr__(self):
        changed = ' has pending updates' if self.changes else ''
        fields = ', '.join('{}={!r}'.format(f, v) for f, v in self.items())
        return '<{model}({fields}){changed}>'.format(
            model=self.__class__.__name__, fields=fields, changed=changed)
