# cosmicray


```python
def authenticate(request):
    ...

api = Route()

api.configure(
    domain='http://localhost:8080',
    domain_env_var='MYAPIENVVAR',
    testing=False,
    auth=('samir', 'superdupersecret'),
    authenticate=authenticate
)

@api.route_handler('/v1/users{id}', methods=['GET'])
def users(request):
    return request.map_model(request.response.json().get('users'))


class Users(Model):
    __fields__ = [
        'id',
        'username',
        'password'
    ]

    __route__ = users

    User = collections.namedtuple('User', __fields__ + ['firstname', 'lastname'])

    def get(self):
        if self.id:
            return self.__route__(Users.User).url_args(id=self.id).get()
        return super(Users, self).get()


>>> api.routes
["<RouteHandler for '/v1/users/{id}'>"]
>>> api.routes.users.path
'/v1/users/{id}'
>>> api.routes.users.__doc__
'
Help on users
....
'
>>> users.get()
[{'id': 12345, 'username': 'foo@example.com', 'password': 'supersecure'}, ...]
>>> users.url_args(id=12345).get()
{'id': 12345, 'username': 'foo@example.com', 'password': 'supersecure', 'firstname': 'Foo', 'lastname': 'Bar'}
>>> users = api.routes.users(User).get()
>>> users
[Users(id=12345, username='foo@example.com', password='supersecure'), ... ]
>>> foo = users[0]
>>> foo.get()
User(id=12345, username='foo@example.com', password='supersecure', firstname='Foo', lastname='Bar')
```