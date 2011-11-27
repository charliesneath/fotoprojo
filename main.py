# upgrade to django 1.2
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings' 
from google.appengine.dist import use_library
use_library('django', '1.2')

# my modules
import picasa_feed

import auth
import datetime
import logging
import urllib
import httplib2
import albums
import Cookie
import time
from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import namespace_manager
            
class Logout(webapp.RequestHandler):
    def get(self):
        # delete twitter cookie
        self.response.headers.add_header(
            'Set-Cookie','twitter_user_id='
        )
        logout_url = users.create_logout_url('/')
        self.redirect(logout_url)
            
class Init(webapp.RequestHandler):
    def get(self):
        services = ('google', 'twitter')
        for service in services:
            namespace_manager.set_namespace(service)
            consumer = auth.OAuthConsumer(
                token_secret = '',
                consumer_key = '',
                consumer_secret = '')
            consumer.put()
        namespace_manager.set_namespace('')
    
application = webapp.WSGIApplication([
                                        ('/', picasa_feed.PicasaFeed),
                                        ('/authenticate', auth.OAuth),
                                        ('/init', Init),
                                        ('/logout', Logout)
                                     ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()