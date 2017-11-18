# -*- coding: utf-8 -*-

import json
import string

import requests

from . import config
from . import util


class Cosmicray(object):
    '''
    Cosmicray app is created to hold the overarching configurations and meta data for an api client

    :param name: App name and User-Agent header
    :param domain: Domain name. Default: http://localhost:8080
    :param home_dir: Apps home directory to store artifact files, such as credentials
        the full path for the home directory will be ``~/.cosmicray/{home_dir}``

    Usage::

        >>> api = Cosmicray('cosmicray/myapp', 'http://mydomain.com', home_dir='myapp')
    '''
    def __init__(self, name, domain='http://localhost:8080', home_dir=None):
        self.name = name
        self.routes = []
        self.config = config.Config({
            'domain': domain,
            'headers': {'User-Agent': self.name},
            'requests_kwargs': {},
            'disable_validation': False,
            'home_dir': home_dir
        })
        self.authenticator = None

    def write_artifact_file(self, config_variable, data, as_json=False):
        fpath = self.config[config_variable]
        data = json.dumps(data) if as_json else data
        util.write_artifact_file(fpath, data)

    def read_artifact_file(self, config_variable, as_json=False):
        fpath = self.config[config_variable]
        data = util.read_artifact_file(fpath)
        return json.loads(data) if as_json else data

    def route(self, path, methods, params=None, urlargs=None, headers=None):
        '''Decorator @route(path, methods, headers, params, urlargs, headers)

        :param path: Uri of type str or string formatter.
        :param methods: list of all allowed methods
        :param params: list of query parameters of type cosmicray.util.QueryParam
        :param urlargs: list of required url arguments
        :param headers: dict representing request headers
        :returns decorates the provided function

        Usage::

            >>> api = Cosmicray('cosmicray/myapp')
            >>> api.route('/v1/coolstuff/{id}', ['GET', 'POST', 'PUT', 'DELETE'])
            ... def coolstuff(response):
            ...     return response.json()
            >>> coolstuff(json={'name': 'magic'}).post()
            >>> coolstuff(urlargs={'id': 12345}).get()
            >>> coolstuff(urlargs={'id': 12345}, json={'name': 'black magic'}).put()
            >>> coolstuff(urlargs={'id': 12345}).delete()

        '''
        handler = RouteHandler(self, path, methods, params, urlargs, headers)
        self.routes.append(handler)
        return handler.decorate

    def configure(self, domain=None, headers=None, **kwargs):
        '''
        :param domain: Set the domain name that the app will use
        :param headers: Set any headers that all requests must have
        :param **kwargs: Globally configure the underlying module used for
            making requests, which in this case it is `requests`
        '''
        self.config.update({
            'domain': domain or self.domain,
            'headers': headers or {},
            'requests_kwargs': kwargs
        })

    def set_authenticator(self, authenticator):
        '''
        :param authentiator: Callback to authenticate each request.
             The callback must accept :class:`Request <Request>` as the only
             argument and return :class:`Request <Request>`

        Example::

            >>> def authenticator(request):
            ...     auth = my_custom_auth_function( ... )
            ...     return request.set_headers({'X-AUTH-TOKEN': auth['token']})
        '''
        self.authenticator = authenticator

    def __repr__(self):
        return '<{app} app for {name}>'.format(
            app=self.__class__.__name__, name=self.name)


class RouteHandler(object):
    def __init__(self, app, path, methods, params, urlargs, headers):
        self.app = app
        self.path = path
        self.methods = methods
        self.params = params
        self.urlargs = urlargs
        self.headers = headers
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
        if handler.headers:
            self.requests_args['headers'].update(handler.headers)
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
        self.urlargs = dict((k, v) for k, v in self.urlargs.items() if v not in [None, ''] )
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
        if self.handler.app.config['disable_validation']:
            return
        if method not in self.handler.methods:
            raise TypeError('Method {!r} is not supported by {!r}'.format(
                method, self.handler))

    def set_param_defaults(self, actual, expected):
        if self.handler.app.config['disable_validation']:
            return
        if expected:
            missing = []
            if not actual:
                raise ValueError('{!r} requires parameters: '.format(
                    self.handler, ', '.join((e.name for e in expected))))
            for param in expected:
                if param.name not in actual:
                    if param.default is not None:
                        value = param.default() if callable(param.default) else param.default
                        actual[param.name] = value
                    elif param.required:
                        missing.append(param.name)
                else:
                    value = actual[param.name]
                    if param.enums and value not in param.enums:
                        raise ValueError('{!r} invalid value for {}: {}'.format(
                            self.handler, param, value))
                    elif param.validate:
                        param.validate(value)
            if missing:
                raise ValueError('{!r} requires parameters: {}'.format(
                    self.handler, ', '.join(missing)))
        return actual

    def request(self, method):
        self.set_param_defaults(
            self.requests_args['params'], self.handler.params)
        self.set_param_defaults(
            self.urlargs, self.handler.urlargs)
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

    def get_value(self, key, args, kwargs):
        try:
            return kwargs[key]
        except KeyError as error:
            return ''
        return Formatter.get_value(key, args, kwargs)
