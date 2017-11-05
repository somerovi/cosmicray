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
        for field in self.__ignorefields__:
            fields.pop(field, None)
        for field in self.__fields__:
            setattr(self, field, fields.pop(field, None))
        if fields:
            print('Got extra fields: {}'.format(', '.join(fields.keys())))

    def items(self):
        return [(field, getattr(self, field)) for field in self.__fields__]

    def as_dict(self):
        return dict((k, v) for k, v in self.items())

    def track_changes(self, field):
        changes = self.__dict__.get('changes')
        if changes and field in self.__fields__:
            self.changes.append(name)

    def clear_changes(self):
        self.changes = []

    def __get_route(self):
        return self.__route__(self)

    @property
    def create_payload(self):
        return self.as_dict()

    @property
    def update_payload(self):
        return self.as_dict()

    def set_params(self, **kwargs):
        return self.__get_route().params(**kwargs)

    def set_url_args(self, **kwargs):
        return self.__get_route().url_args(**kwargs)

    def get(self):
        return self.__get_route().get()

    def delete(self):
        return self.__get_route().delete()

    def create(self):
        return self.__get_route().json(self.create_payload).post()

    def update(self):
        return self.__get_route().json(self.update_payload).put()

    @classmethod
    def _make(cls, fields):
        return cls(**fields)

    def __repr__(self):
        fields = ', '.join('{}={!r}'.format(f, v) for f, v in self.items())
        return '<{model}({fields})>'.format(model=self.__class__.__name__, fields=fields)
