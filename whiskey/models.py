from whiskey import app, mongo, lm
from flask.ext.login import 
from bson.objectid import ObjectId
from hashlib import md5

@lm.user_loader
def load_user (userid):
    return User.get({'_id': ObjectID(userid)})

class User (dict):

    def __init__ (self, initdict = None):
        dict.__init__(self)

        self.update({
            'nickname':        	'',
            'email':           	'',
            'ghlogin':          '',
            'profile':          '',
            'active':		False, 
            'posts':            [],
        }

        if (initdict):
            self.update(initdict)

    def is_authenticated (self):
        return True

    def is_active (self):
        return self['active']

    def is_anonymous (self):
        return False

    def get_id (self):
        return unicode(self.id)

    def __repr__ (self):
        return '<User {0!r}>'.format(self['nickname'])

    def avatar (self, size):
        return 'http://www.gravatar.com/avatar/{0}?d=mm&s={1}'.format(md5(self['email']).hexdigest(), str(size))

    def get (self, matchdict):
        return User(mongo.db['users'].find_one(matchdict))

    def get_all (self, matchdict):
        docs = mongo.db['users'].find(matchdict)
        return [User(item) for item in docs]
