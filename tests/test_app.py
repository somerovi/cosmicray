import os.path

import pytest

import cosmicray



APP_NAME = 'sunshine'
APP_DOMAIN = 'http://sunshine.com'


@pytest.fixture
def app(monkeypatch, tmpdir):
    def new_expanduser(path):
        return str(tmpdir.join(path))
    old_expanduser = getattr(os.path, 'expanduser')
    monkeypatch.setattr(os.path, 'expanduser', new_expanduser)
    yield cosmicray.Cosmicray(APP_NAME, domain=APP_DOMAIN)
    monkeypatch.setattr(os.path, 'expanduser', old_expanduser)


def test_app_init(app):
    assert app.get_config('headers').get('User-Agent') == APP_NAME
    assert app.get_config('domain') == APP_DOMAIN


def test_app_configure(app):
    new_domain = 'http://example.com'
    new_headers = {'Content-Type': 'application/json'}
    new_params = {'test': 'true'}
    new_urlargs = {'version': 'v1'}
    new_authenticator = lambda request: request
    new_auth = ('ray', 'ofsunshine')
    new_extra = {'verify': False}
    app.configure(domain=new_domain,
                  headers=new_headers,
                  params=new_params,
                  urlargs=new_urlargs,
                  authenticator=new_authenticator,
                  auth=new_auth,
                  **new_extra)
    headers = app.get_config('headers')
    params = app.get_config('params')
    urlargs = app.get_config('urlargs')
    authenticator = app.get_config('authenticator')
    auth = app.get_config('auth')
    extra  = app.get_config('extra')
    assert app.get_config('domain') == new_domain
    assert headers.get('User-Agent') == APP_NAME
    assert headers.get('Content-Type') == 'application/json'
    assert params == new_params
    assert urlargs == new_urlargs
    assert authenticator('works') == 'works'
    assert auth == new_auth
    assert extra == new_extra


def test_app_route(app):
    app.configure(headers={'Some-Header': 'important'},
                  urlargs={'version': 'v1'})

    path = '{version}/{arg}/path/to/resource/{id}'
    methods = ['GET']
    params = [
        cosmicray.Param('notrequired'),
        cosmicray.Param('required', required=True),
        cosmicray.Param('default', default='true'),
        cosmicray.Param('callback', default=lambda obj, context: 'calledback'),
        cosmicray.Param('options', options=['this'])
    ]
    urlargs = [
        cosmicray.Param('arg', default='this')
    ]
    headers = {'X-REQUEST-ID': '123456789', 'Some-Header': 'not important'}

    @app.route(path, methods, params=params, urlargs=urlargs, headers=headers)
    def some_path(response):
        return response.json()

    request = some_path(method='GET')

    # Missing required parameters
    with pytest.raises(TypeError):
        request.validate()

    # Required parameters are added, but invalid
    request.update(params={'required': 'provided', 'options': 'invalid'})
    with pytest.raises(TypeError):
        request.validate()

    # Parameters are valid
    request.update(params={'options': 'this'})
    request.validate()
    assert request.params == {
        'required': 'provided',
        'options': 'this',
        'default': 'true',
        'callback': 'calledback'}
    assert request.urlargs == {'version': 'v1', 'arg': 'this'}
    assert request.headers == {
        'Some-Header': 'not important',
        'X-REQUEST-ID': '123456789',
        'User-Agent': 'sunshine'}

    url = '{}/{}'.format(APP_DOMAIN, path).format(
        version='v1', id='', arg='this').strip('/')
    assert request.url == url
    request.override(headers=None, params=None)
    assert request.headers is None
    assert request.params is None
