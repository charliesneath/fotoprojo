from google.appengine.ext import db
import datetime

class AuthenticatedUsers(db.Model):
    email = db.StringProperty()