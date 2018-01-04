# -*- coding: utf-8 -*-
import collections
import inspect
import importlib


class Model(object):
    __slots__ = (
        '__changes__',
        '__model_attr__'
    )
    __ignore__ = []
    __route__ = None

    def __init__(self, **kwargs):
        self.__changes__ = []
        self.__model_attr__ = {}
        self.setfields(kwargs, track=False)
        self.clear_changes()

    def setfields(self, fields, track=True):
        for field in self.__slots__:
            try:
                default = getattr(self, field)
            except AttributeError:
                default = None
            value = fields.pop(field, default)
            setattr(self, field, value)
            if track:
                self.track_changes(field, value)
        for field in self.__ignore__:
            fields.pop(field, None)
        if fields:
            print('{!r} got extra fields: {}'.format(
                self.__class__.__name__, ', '.join(fields.keys())))

    def items(self):
        '''Returns iterator of key-value pairs from the objects fields'''
        return ((field, getattr(self, field)) for field in self.__slots__)

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
        self.__changes__.append(field)

    def clear_changes(self):
        '''Clears tracking of changes'''
        self.__changes__ = []

    def get_create_payload(self):
        '''POST request default payload: { "json" : self.dict }'''
        return {'json': self.dict}

    def get_update_payload(self):
        '''PUT request default payload: { "json" : self.dict }'''
        return {'json': self.dict}

    def __call__(self, **kwargs):
        '''Returns :class:`cosmicray.Request` with :class:`Model`.__class__ as the model_cls
        and ``self.dict`` as urlargs'''
        return self.__route__(
            model_cls=self.__class__, urlargs=self.dict, **kwargs)

    def get(self):
        '''GET request'''
        self.dict = self.__route__(urlargs=self.dict).get()
        return self

    def delete(self):
        '''DELETE request'''
        return self().delete()

    def create(self):
        '''POST request. Uses :class:`Model.get_create_payload` as the POST body'''
        return self(**self.get_create_payload()).post()

    def update(self):
        '''PUT request. Uses :class:`Model.get_update_payload` as the PUT body'''
        return self(**self.get_update_payload()).put()

    def update_related(self):
        '''Sends PUT request for all related models and routes'''
        for model_attr in self.__model_attr__.values():
            model_attr.update()

    def create_related(self):
        '''Sends POST request for all related models and routes'''
        for model_attr in self.__model_attr__.values():
            model_attr.create()

    def delete_related(self):
        '''Sends DELETE request for all related models and routes'''
        for model_attr in self.__model_attr__.values():
            model_attr.delete()

    @classmethod
    def _make(cls, fields):
        return cls(**fields)

    def __repr__(self):
        changed = ' has pending updates' if self.__changes__ else ''
        fields = ', '.join('{}={!r}'.format(f, v) for f, v in self.items())
        return '<{model}({fields}){changed}>'.format(
            model=self.__class__.__name__, fields=fields, changed=changed)


class ModelAttribute(object):
    '''
    :param model_cls_name: Class name for the related model
    :param route: instance of ``cosmicray.Route``
    :params urlargs: URL formatting parameters as dict object
    :param params: URL query parameters as dict object
    :param is_sequence: Specify True if attribute is a list of Models, False otherwise
    :params get_create_payload: Callable, accepts instance of ``cosmicray.Model`` as its only
        argument and returns POST request payload arguments
    :params get_update_payload: Callable, accepts instance of ``cosmicray.Model`` as its only
        argument and returns PUT request payload arguments
    '''
    def __init__(self, model_cls_name, route, urlargs, params, is_sequence,
                 get_create_payload, get_update_payload):
        self.model_cls_name = model_cls_name
        self.route = route
        self.urlargs = urlargs or {}
        self.params = params or {}
        self.is_sequence = is_sequence
        self.get_update_payload = get_update_payload
        self.get_create_payload = get_create_payload

    def getter(self, model_ref):
        return self._get_model_instance_attribute(model_ref).getter()

    def setter(self, model_ref, obj):
        return self._get_model_instance_attribute(model_ref).setter(obj)

    def deleter(self, model_ref):
        return self._get_model_instance_attribute(model_ref).deleter()

    def _get_model_instance_attribute(self, model_ref):
        if self not in model_ref.__model_attr__:
            model_ref.__model_attr__[self] = ModelInstanceAttribute(
                model_attr=self, model_ref=model_ref)
        return model_ref.__model_attr__[self]

    def __repr__(self):
        return '<{} for {}>'.format(self.__class__.__name__, self.model_cls_name)


class ModelInstanceAttribute(object):
    def __init__(self, model_attr, model_ref):
        self.model_attr = model_attr
        self.model_ref = model_ref
        self.model_obj = None

    @property
    def model_cls(self):
        if self.model_attr.model_cls_name is not None:
            module_name, _, classname = self.model_attr.model_cls_name.rpartition('.')
            module = importlib.import_module(module_name)
            return getattr(module, classname)

    def __nonzero__(self):
        return self.model_obj is not None

    def __getattr__(self, attr):
        return getattr(self.model_obj, attr)

    def __getitem__(self, name):
        return self.model_obj.__getitem__(name)

    def __setitem__(self, name, value):
        return self.model_obj.__setitem__(name, value)

    def __delitem__(self, name):
        return self.model_obj.__delitem__(name)

    def __iter__(self):
        return self.model_obj.__iter__()

    def __next__(self):
        return self.model_obj.__next__()

    @property
    def value(self):
        return self.model_obj

    def clear(self):
        self.model_obj = None

    def getter(self):
        self.get()
        return self

    def setter(self, obj):
        self.model_obj = obj

    def deleter(self):
        self.clear()

    def __call__(self, **kwargs):
        urlargs = {}
        for urlarg, param in self.model_attr.urlargs.items():
            if isinstance(param, ModelParam):
                urlargs[urlarg] = param.validate(getattr(self.model_ref, param.name))
            else:
                urlargs[urlarg] = param
        if self.model_attr.route:
            return self.model_attr.route(model_cls=self.model_cls, urlargs=urlargs, **kwargs)
        return self.model_cls()(**kwargs).set_urlargs(urlargs)

    def get(self):
        if self.model_obj is None:
            self.model_obj = self._as_sequence(self().get())
        return self.model_obj

    def update(self):
        success = True
        try:
            if self.model_attr.get_update_payload is None:
                return self._as_sequence(self.model_obj.update())
            return self._as_sequence(
                self(**self.model_attr.get_update_payload(self.model_ref)).put())
        except:
            success = False
            raise
        finally:
            if success:
                self.model_obj = None

    def create(self):
        success = True
        try:
            if self.model_attr.get_create_payload is None:
                return self._as_sequence(self.model_obj.create())
            return self._as_sequence(
                self(**self.model_attr.get_create_payload(self.model_ref)).post())
        except:
            success = False
            raise
        finally:
            if success:
                self.model_obj = None

    def delete(self):
        return self().delete()

    def _as_sequence(self, result):
        return list(result) if self.model_attr.is_sequence else result

    def __repr__(self):
        return '<ModelInstanceAttribute for {}>'.format(repr(self.model_obj))


def relationship(model_cls=None, route=None, urlargs=None, params=None, is_sequence=False,
                 get_create_payload=None, get_update_payload=None):
    '''Returns property with a getter, setter, and deleter method'''
    if model_cls is None and route is None:
        raise ValueError("model_cls and route cannot both be None")
    frame = inspect.stack()[1]
    module_name = inspect.getmodule(frame[0]).__name__
    model_cls_name = '{}.{}'.format(module_name, model_cls)
    model_attr = ModelAttribute(
        model_cls_name, route, urlargs, params, is_sequence,
        get_create_payload, get_update_payload)
    doc = '<ModelAttribute for {}>'.format(
        model_cls.__class__.__name__ if model_cls else route.path)
    return property(model_attr.getter, model_attr.setter, model_attr.deleter, doc)


class ModelParam(object):
    def __init__(self, name):
        self.name = name

    def validate(self, obj, context=None):
        if obj is None:
            raise TypeError('Invalid value for {}: {!r}'.format(self.name, obj))
        return obj
