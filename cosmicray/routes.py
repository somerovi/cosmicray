# -*- coding: utf-8 -*-


import string

import requests

from . import config
from . import util


class Cosmicray(object):
    '''
    >>> api = Cosmicray('cosmicray/myapp')
    '''
    def __init__(self, name, domain='http://localhost:8080'):
        '''
        :param name: App name and User-Agent header
        :param domain: Domain name. Default: http://localhost:8080
        '''
        self.name = name
        self.routes = []
        self.config = config.Config({
            'domain': domain,
            'headers': {'User-Agent': self.name},
            'requests_kwargs': {}
        })
        self.authenticator = None

    def route(self, path, methods, params=None, urlargs=None):
        '''Decorator @route(path, methods, headers, params, urlargs)

        >>> api = Cosmicray('cosmicray/myapp')
        >>> api.route('/v1/coolstuff/{id}', ['GET', 'POST', 'PUT', 'DELETE'])
        >>> def coolstuff(response):
        >>>     return response.json()
        >>> coolstuff(json={'name': 'magic'}).post()
        {'id': 12345}
        >>> coolstuff(urlargs={'id': 12345}).get()
        {'id': 12345, 'name': 'magic'}
        >>> coolstuff(urlargs={'id': 12345}, json={'name': 'black magic'}).put()
        {'id': 12345, 'name': 'black magic'}
        >>> coolstuff(urlargs={'id': 12345}).delete()
        {'id': 12345, 'name': 'black magic'}

        :param path: Uri of type str or string formatter.
        :param methods: list of all allowed methods
        :param params: list of query parameters of type cosmicray.util.QueryParam
        :param urlargs: list of required url arguments
        :returns decorates the given function
        '''
        handler = RouteHandler(self, path, methods, params, urlargs)
        self.routes.append(handler)
        return handler.decorate

    def configure(self, domain=None, authenticator=None, headers=None, **kwargs):
        '''
        :param domain: Set the domain name that the app will use
        :param authentiator: Callback to authenticate each request
            >>> def authenticator(request):
            ...     auth = my_custom_auth_function( ... )
            ...     return request.set_headers({'X-AUTH-TOKEN': auth['token']})
        :param headers: Set any headers that all requests must have
        :param **kwargs: Globally configure the underlying module used for
            making requests, which in this case it is `requests`
        '''
        self.config.update({
            'domain': domain or self.domain,
            'headers': headers or {},
            'requests_kwargs': kwargs
        })
        self.authenticator = authenticator

    def __repr__(self):
        return '<{app} app for {name}>'.format(
            app=self.__class__.__name__, name=self.name)


class RouteHandler(object):
    def __init__(self, app, path, methods, params, urlargs):
        self.app = app
        self.path = path
        self.methods = methods
        self.params = params
        self.urlargs = urlargs
        self.response_handler = None

    def decorate(self, response_handler):
        self.response_handler = response_handler
        return self

    def handle_response(self, model_cls, response):
        return self.map_model(
            model_cls, self.response_handler(response))

    def map_model(self, model_cls, data):
        if model_cls is not None:
            _make = getattr(model_cls, '_make')
            try:
                return _make(data)
            except TypeError:
                return map(_make, data)
        return data

    def authenticate(self, request):
        if self.app.authenticator:
            return self.app.authenticator(request)
        return request

    @property
    def url(self):
        domain = self.app.config['domain']
        return '{domain}/{path}'.format(
            domain=domain.rstrip('/'),
            path=self.path.lstrip('/'))

    def __eq__(self, obj):
        if isinstance(obj, RouteHandler):
            return self.path == obj.path
        elif isinstance(obj, str):
            return self.path == obj
        raise TypeError('Incompatible type: {}'.format(type(obj)))

    def __call__(self, model_cls=None, urlargs=None, **requests_args):
        return Request(self).set(model_cls, urlargs, **requests_args)

    def __repr__(self):
        return '<{name} for {path!r}>'.format(
            name=self.__class__.__name__, path=self.path)


class Request(object):
    def __init__(self, handler):
        self.handler = handler
        self.requests_args = {
            'params': {},
            'json': None,
            'data': None,
            'headers': handler.app.config.getcopy('headers'),
        }
        self.requests_args.update(handler.app.config.getcopy('requests_kwargs'))
        self.urlargs = {}
        self.model_cls = None

    def is_request_for(self, *route_handlers):
        return any(self.handler == handler for handler in route_handlers)

    def set(self, model_cls=None, urlargs=None, **kwargs):
        self.model_cls = model_cls
        self.set_urlargs(urlargs)
        self.requests_args.update(**kwargs)
        return self

    def set_urlargs(self, from_dict_obj=None,  **kwargs):
        self.urlargs.update(
            from_dict_obj or {}, **kwargs)
        return self

    def set_headers(self, from_dict_obj=None, **kwargs):
        self.requests_args['headers'].update(
            from_dict_obj or {}, **kwargs)
        return self

    def set_params(self, from_dict_obj=None, **kwargs):
        self.requests_args['params'].update(
            from_dict_obj or {}, **kwargs)
        return self

    def set_payload(self, data=None, json=None):
        self.requests_args.update({'data': data, 'json': json})
        return self

    def validate_method(self, method):
        if method not in self.handler.methods:
            raise TypeError('Method {!r} is not supported by {!}'.format(
                method, self.handler))

    def validate_params(self):
        if self.handler.params:
            missing = []
            for param in self.handler.params:
                if param.name not in self.requests_args['params']:
                    if param.value is not None:
                        value = param.value() if callable(param.value) else param.value
                        self.requests_args['params'][param.name] = value
                    elif param.required:
                        missing.append(param.name)
            if missing:
                raise ValueError('{!r} requires query parameters: {}'.format(
                    self.handler, ', '.join(missing)))

    def request(self, method):
        self.validate_params()
        self.validate_method(method)
        self.handler.authenticate(self)
        url = DefaultUrlFormatter().format(self.handler.url, **self.urlargs)
        request = getattr(requests, method.lower())
        response = request(url, **self.requests_args)
        try:
            response.raise_for_status()
        except Exception as error:
            print(response.text)
            raise error
        return response

    def get(self):
        return self.handler.handle_response(
            self.model_cls, self.request('GET'))

    def delete(self):
        return self.handler.handle_response(
            self.model_cls, self.request('DELETE'))

    def post(self):
        return self.handler.handle_response(
            self.model_cls, self.request('POST'))

    def put(self):
        return self.handler.handle_response(
            self.model_cls, self.request('PUT'))

    def head(self):
        return self.handler.handle_response(
            self.model_cls, self.request('HEAD'))

    def options(self):
        return self.handler.handle_response(
            self.model_cls, self.request('OPTIONS'))

    def __repr__(self):
        return '<Request for {}>'.format(self.handler.path)


class DefaultUrlFormatter(string.Formatter):
    def __init__(self, required=None, *args, **kwargs):
        super(DefaultUrlFormatter, self).__init__(*args, **kwargs)
        self.required = required

    def get_value(self, key, args, kwargs):
        try:
            return kwargs[key]
        except KeyError as error:
            if self.required and key not in self.required:
                raise KeyError(
                    'Missing required url argument: {}'.format(key))
            return ''
        return Formatter.get_value(key, args, kwargs)
