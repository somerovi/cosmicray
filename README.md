# Cosmicray
###### Develop a client for your http API and document its quirks and features

Cosmicray is a http client API development framework. It provides the basic building blocks for
defining enpoints, handling requests responses and automatically converting them to Models.


### Basics: Defining routes and route handlers and making requests

```python
>>> from cosmicray import Cosmicray
>>>
>>> api = Cosmicray('cosmicray/myapp')
>>> api.route('/v1/coolstuff/{id}', ['GET', 'POST', 'PUT', 'DELETE'])
>>> def coolstuff(request):
...     return request.response.json()
>>> coolstuff(json={'name': 'magic'}).post()
{'id': 12345}
>>> coolstuff(urlargs={'id': 12345}).get()
{'id': 12345, 'name': 'magic'}
>>> coolstuff(urlargs={'id': 12345}, json={'name': 'black magic'}).put()
{'id': 12345, 'name': 'black magic'}
>>> coolstuff(urlargs={'id': 12345}).delete()
{'id': 12345, 'name': 'black magic'}
```

### Basics: Customizing request

```python
>>> coolstuff(urlargs={'id': 12345},
...           headers={'Content-Type': 'application/json'},
...           params={'debug': True}).get()
```

You can also pass in keyword arguments for the `requests` module:

```python
>>> coolstuff(urlargs={'id': 12345},
...           headers={'Content-Type': 'application/json'},
...           params={'debug': True},
...           json={'name': 'white magic'}).put()
```

### Basics: Authenticating requests

Most often before you can access resources, you'll need to authenticate and pass authentication
parameters to each request. Cosmicray has you covered!

```python
def authenticator(request):
    if not request.is_request_for(auth):
        auth = auth(json={'username': 'me', 'password': 'mysecret'}).post()
        return request.set_headers({'X-AUTH-TOKEN': auth['token']})


@api.route('/auth', ['POST'])
def auth(request):
    return request.response.json()

@api.route('/private/resource', ['GET'])
def private_resource(request):
    return request.response.json()

api.configure(authenticator)

# Now the private resourse will be automatically updated to include auth headers
private_resource.get()
```

### Models

```python
>>> from cosmicray import Model
>>>
>>> class CoolStuff(Model):
...     __route__ = coolstuff
...     __fields__ = [
...         'id',
...         'name'
...     ]
>>> obj = CoolStuff(name="Magic")
>>> obj
<CoolStuff(id=None, name='magic')>
>>> obj.create()
```

If you don't want to use `cosmicray.Model` as your base, you can define your own OR
even use just use `collections.namedtuple` as the model.

```python
>>> class MyModel(object):
...     @classmethod
...     def _make(cls, response):
...         obj = cls()
...         ... do stuff with the response
...         return obj
```
