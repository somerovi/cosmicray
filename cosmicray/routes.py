import collections
import os
import string

import requests


QueryParam = collections.namedtuple('QueryParam', ['name', 'value', 'required'])

def param(name, value=None, required=False):
    return QueryParam(name=name, value=value, required=required)


class Route(object):
    '''
    Base for all route handling
    '''
    def __init__(self, name):
        self.name = name
        self.routes = []
        self.config = {
            'domain': 'http://localhost:8080',
            'headers': requests.utils.default_headers()
        }
        self.config['headers'].update({'User-Agent': self.name})

    def route_handler(self, path, methods, params=None):
        '''
        Decorator
        @route_handler(path, methods, headers, params)
        '''
        handler = RouteHandler(self, path, methods, params)
        self.routes.append(handler)
        return handler.decorate

    def configure(self, domain, headers=None, auth=None):
        '''
        Route.configure(
            domain='http://localhost:8080',
            domain_env_var='APIV3'
        )
        '''
        self.config['domain'] = domain
        if headers:
            self.config['headers'].update(headers)

    def get_headers(self):
        return dict(self.config['headers'])

    def get_domain(self):
        return self.config['domain']

    def __repr__(self):
        return '<Route for {name}>'.format(name=self.name)


class RouteHandler(object):
    def __init__(self, route, path, methods, params):
        self.route = route
        self.path = path
        self.methods = methods
        self.params = params
        self.response_handler = None

    def decorate(self, response_handler):
        self.response_handler = response_handler
        return self

    def handle_response(self, *args):
        return self.response_handler(*args)

    @property
    def url(self):
        return '{domain}/{path}'.format(
            domain=self.route.get_domain().rstrip('/'),
            path=self.path.lstrip('/'))

    def get_headers(self):
        return self.route.get_headers()

    def __call__(self, model):
        return Request(self).model(model)

    def model(self, model):
        return Request(self).model(model)

    def params(self, **params):
        return Request(self).params(**params)

    def headers(self, **headers):
        return Request(self).headers(**headers)

    def url_args(self, **kwargs):
        return Request(self).url_args(**kwargs)

    def json(self, payload):
        return Request(self).json(payload)

    def get(self):
        return Request(self).get()

    def __repr__(self):
        return '<RouteHandler for {path!r}>'.format(path=self.path)


class Request(object):
    def __init__(self, handler):
        self.handler = handler
        self.requests_args = {
            'params': {},
            'auth': None,
            'json': None,
            'data': None,
            'headers': handler.get_headers(),
        }
        self._url_args = {}
        self._model = None
        self.response = None

    def model(self, model):
        self._model = model
        args = model.as_dict()
        self.url_args(**args)
        return self

    def url_args(self, **url_args):
        self._url_args.update(url_args)
        return self

    def headers(self, **headers):
        self.requests['headers'].update(headers)
        return self

    def params(self, **params):
        self.requests_args['params'].update(params)
        return self

    def json(self, payload):
        self.requests_args['json'] = payload
        return self

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

    def map_model(self, data):
        if self._model:
            _make = getattr(self._model, '_make')
            try:
                return _make(data)
            except TypeError:
                return map(_make, data)
        return data

    def request(self, method):
        url = DefaultUrlFormatter().format(self.handler.url, **self._url_args)
        request = getattr(requests, method.lower())
        response = request(url, **self.requests_args)
        response.raise_for_status()
        self.response = response
        return self

    def get(self):
        return self.handler.handle_response(self.request('GET'))

    def delete(self):
        return self.handler.handle_response(self.request('DELETE'))

    def post(self):
        return self.handler.handle_response(self.request('POST'))

    def put(self):
        return self.handler.handle_response(self.request('PUT'))

    def __repr__(self):
        return '<Request for {}>'.format(self.handler.uri)


class DefaultUrlFormatter(string.Formatter):
    def __init__(self, required=None, *args, **kwargs):
        super(DefaultFormatter, self).__init__(*args, **kwargs)
        self.required = required

    def get_value(self, key, args, kwargs):
        if isinstance(key, basestring):
            try:
                return kwargs[key]
            except KeyError:
                return ''
        else:
            return Formatter.get_value(key, args, kwargs)
