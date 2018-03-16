# -*- coding: utf-8 -*-
import collections
import inspect
import importlib
import time


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

    def __bool__(self):
        return any(value is not None for _, value in self.items())

    def __nonzero__(self):
        return self.__bool__()

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
    :param model_cls_name: Class name for the related model. If both route and model class are provided, the
        route will take precedence.
    :param route: instance of ``cosmicray.Route``. If both route and model class are provided, the
        route will take precedence.
    :params urlargs: URL formatting parameters as dict object
    :param params: URL query parameters as dict object
    :param is_sequence: Specify True if attribute is a list of Models, False otherwise
    :param get_create_payload: Callable, accepts instance of ``cosmicray.Model`` as its only
        argument and returns POST request payload arguments
    :param get_update_payload: Callable, accepts instance of ``cosmicray.Model`` as its only
        argument and returns PUT request payload arguments
    :param get: Overrides ``GET`` request. Callable which accepts two arguments, ``model_ref`` and ``model_obj``, where ``model_ref`` is an instance of the class that the model attribute belongs to. And ``model_obj`` is an instance of ``ModelInstanceAttribute``, in other words, the related model object or response from the request
    :param create:  Overrides ``POST`` request. Callable which accepts two arguments, ``model_ref`` and ``model_obj``, where ``model_ref`` is an instance of the class that the model attribute belongs to. And ``model_obj`` is an instance of ``ModelInstanceAttribute``, in other words, the related model object or response from the request
    :param update: Overrides ``PUT`` request. Callable which accepts two arguments, ``model_ref`` and ``model_obj``, where ``model_ref`` is an instance of the class that the model attribute belongs to. And ``model_obj`` is an instance of ``ModelInstanceAttribute``, in other words, the related model object or response from the request
    :param delete: Overrides ``DELETE`` request. Callable which accepts two arguments, ``model_ref`` and ``model_obj``, where ``model_ref`` is an instance of the class that the model attribute belongs to. And ``model_obj`` is an instance of ``ModelInstanceAttribute``, in other words, the related model object or response from the request
    :param ttl: Timeout in seconds for how long to cache result of a request. Default: None, never expire
    :param is_static: Specify if attribute can be accessed like a class attribute

    '''
    def __init__(self, model_cls_name, route, urlargs, params, is_sequence,
                 get_create_payload, get_update_payload,
                 get=None, create=None, update=None, delete=None, ttl=None,
                 is_static=False, lazy=False):
        self.model_cls_name = model_cls_name
        self.route = route
        self.urlargs = urlargs or {}
        self.params = params or {}
        self.is_sequence = is_sequence
        self.get_update_payload = get_update_payload
        self.get_create_payload = get_create_payload
        self.get_method = get
        self.create_method = create
        self.update_method = update
        self.delete_method = delete
        self.ttl = ttl
        self.is_static = is_static
        self.lazy = lazy
        self._static = None

    def __get__(self, model_ref, model_cls):
        if self.is_static:
            return self.get_static_model_instance_attribute(model_cls).getter()
        return self._get_model_instance_attribute(model_ref).getter()

    def __set__(self, model_ref, value):
        if self.is_static:
            raise AttributeError('Cannot set static attribute')
        return self._get_model_instance_attribute(model_ref).setter(value)

    def __delete__(self, model_ref):
        if self.is_static:
            raise AttributeError('Cannot delete static attribute')
        return self._get_model_instance_attribute(model_ref).deleter()

    def _get_model_instance_attribute(self, model_ref):
        if self not in model_ref.__model_attr__:
            model_ref.__model_attr__[self] = ModelInstanceAttribute(
                model_attr=self, model_ref=model_ref)
        return model_ref.__model_attr__[self]

    def get_static_model_instance_attribute(self, model_cls):
        if self._static is None:
            self._static = ModelInstanceAttribute(model_attr=self, model_ref=model_cls)
        return self._static

    def __repr__(self):
        return '<{} for {}>'.format(self.__class__.__name__, self.model_cls_name)


class ModelInstanceAttribute(object):
    '''
    :param model_attr: Instance of ``cosmicray.model.ModelAttribute``
    :param model_ref: Instance of sub-class of``cosmicray.model.Model``
    '''
    def __init__(self, model_attr, model_ref):
        self.model_attr = model_attr
        self.model_ref = model_ref
        self.value = None
        self._fetched_on = None

    @property
    def model_cls(self):
        if self.model_attr.model_cls_name is not None:
            module_name, _, classname = self.model_attr.model_cls_name.rpartition('.')
            module = importlib.import_module(module_name)
            return getattr(module, classname)

    @property
    def route(self):
        return self.model_attr.route

    def __bool__(self):
        return self.value is not None

    def __nonzero__(self):
        return self.__bool__()

    def __getattr__(self, attr):
        return getattr(self.value, attr)

    def __getitem__(self, name):
        return self.value.__getitem__(name)

    def __setitem__(self, name, value):
        return self.value.__setitem__(name, value)

    def __delitem__(self, name):
        return self.value.__delitem__(name)

    def __iter__(self):
        return self.value.__iter__()

    def __next__(self):
        return self.value.__next__()

    def __len__(self):
        return self.value.__len__()

    def clear(self):
        self.value = None

    def clear_if_expired(self):
        if self.expired():
            self.clear()

    def getter(self):
        if not self.model_attr.lazy:
            self.clear_if_expired()
            if self.value is None:
                self.get()
        return self

    def setter(self, obj):
        self.value = obj

    def deleter(self):
        self.clear()

    def __call__(self, **kwargs):
        urlargs = {}
        for name, param in self.model_attr.urlargs.items():
            if isinstance(param, ModelParam):
                urlargs[name] = param.validate(getattr(self.model_ref, param.name))
            else:
                urlargs[name] = param
        params = {}
        for name, param in self.model_attr.params.items():
            if isinstance(param, ModelParam):
                params[name] = param.validate(getattr(self.model_ref, param.name))
            else:
                params[name] = param

        if self.model_attr.route:
            request = self.model_attr.route(
                model_cls=self.model_cls, urlargs=urlargs, params=params)
        else:
            request = self.model_cls()()\
                          .set_urlargs(urlargs)\
                          .set_params(params)
        request.update(**kwargs)
        return request

    def expired(self):
        return (self.model_attr.ttl
                and self._fetched_on and (
                    (time.time() - self._fetched_on) > self.model_attr.ttl))

    def get(self):
        if self.model_attr.get_method:
            self.value = self._as_sequence(
                self.model_attr.get_method(self.model_ref, self))
        else:
            self.value = self._as_sequence(self().get())
        self._fetched_on = time.time()
        return self.value

    def update(self):
        if self.model_attr.update_method:
            return self._as_sequence(
                self.model_attr.update_method(self.model_ref, self))
        if self.model_attr.get_update_payload is None:
            return self._as_sequence(self.value.update())
        return self._as_sequence(
            self(**self.model_attr.get_update_payload(self.model_ref)).put())

    def create(self):
        if self.model_attr.create_method:
            return self._as_sequence(
                self.model_attr.create_method(self.model_ref, self))
        if self.model_attr.get_create_payload is None:
            return self._as_sequence(self.value.create())
        return self._as_sequence(
            self(**self.model_attr.get_create_payload(self.model_ref)).post())

    def delete(self):
        if self.model_attr.delete_method:
            return self._as_sequence(
                self.model_attr.delete_method(self.model_ref, self))
        return self().delete()

    def _as_sequence(self, result):
        return list(result) if result and self.model_attr.is_sequence else result

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)


def relationship(
        model_cls=None, route=None, urlargs=None, params=None,
        is_sequence=False,
        get_create_payload=None, get_update_payload=None,
        get=None, create=None, update=None, delete=None,
        ttl=None, is_static=False, lazy=False):
    '''Returns property-like object with a getter, setter, and deleter method'''
    if model_cls is None and route is None:
        raise ValueError("model_cls and route cannot both be None")
    frame = inspect.stack()[1]
    module_name = inspect.getmodule(frame[0]).__name__
    model_cls_name = '{}.{}'.format(module_name, model_cls)
    model_attr = ModelAttribute(
        model_cls_name, route, urlargs, params, is_sequence,
        get_create_payload, get_update_payload,
        get, create, update, delete, ttl, is_static, lazy)
    return model_attr


class ModelParam(object):
    def __init__(self, name):
        self.name = name

    def validate(self, obj, context=None):
        if obj is None:
            raise TypeError('Invalid value for {}: {!r}'.format(self.name, obj))
        return obj
