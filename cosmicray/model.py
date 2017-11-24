# -*- coding: utf-8 -*-


class Model(object):

    __fields__ = []
    __ignore__ = []
    __route__ = None

    def __init__(self, **kwargs):
        self.setfields(kwargs)
        self.changes = []

    def __setattr__(self, name, value):
        self.track_changes(name, value)
        self.__dict__[name] = value

    def setfields(self, fields):
        for field in self.__fields__:
            try:
                default = getattr(self, field)
            except AttributeError:
                default = None
            setattr(self, field, fields.pop(field, default))
        for field in self.__ignore__:
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
        self.setfields(fields)

    dict = property(get_dict, set_dict, doc='Getter and setter from dict object')

    def __nonzero__(self):
        return any(value is not None for _, value in self.items())

    def track_changes(self, field, new_value):
        '''Tracks which fields have updated values'''
        changes = self.__dict__.get('changes')
        if changes and field in self.__fields__:
            self.changes.append(name)

    def clear_changes(self):
        '''Clears tracking of changes'''
        self.changes = []

    def payload_for_create(self):
        '''POST request default payload: { "json" : self.dict }'''
        return {'json': self.dict}

    def payload_for_update(self):
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
        return self.get_request(**self.payload_for_create()).post()

    def update(self):
        '''PUT request. Uses :class:`Model.update_payload` as the PUT body'''
        return self.get_request(**self.payload_for_update()).put()

    @classmethod
    def _make(cls, fields):
        return cls(**fields)

    def __repr__(self):
        changed = ' has pending updates' if self.changes else ''
        fields = ', '.join('{}={!r}'.format(f, v) for f, v in self.items())
        return '<{model}({fields}){changed}>'.format(
            model=self.__class__.__name__, fields=fields, changed=changed)
