import urllib
import cgi
import httplib2
import logging
from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.api import namespace_manager
import oauth2 as oauth

def create_oauth_client(user, service):
    namespace_manager.set_namespace(service)
    creds = OAuthCredentials(user)
    token = oauth.Token(key = creds.token, secret = creds.token_secret)
    consumer = oauth.Consumer(key = creds.consumer_key, secret = creds.consumer_secret)
    client = oauth.Client(consumer, token)
    namespace_manager.set_namespace('')
    return client

class OAuth(webapp.RequestHandler):
    '''authenticates the current user'''
    service = None
    
    def __init__(self):
        # set the service being authenticated
        #set urls for OAuth authentication endpoints
        self.request_token_url = {
            'google': 'https://www.google.com/accounts/OAuthGetRequestToken',
            'twitter': 'http://twitter.com/oauth/request_token'
        }
        self.authorize_url = {
            'google': 'https://www.google.com/accounts/OAuthAuthorizeToken',
            'twitter': 'https://api.twitter.com/oauth/authenticate'
        }
        self.access_token_url = {
            'google': 'https://www.google.com/accounts/OAuthGetAccessToken',
            'twitter': 'https://api.twitter.com/oauth/access_token' 
        }

    def get(self):
        '''directs the authentication request and sets the namespace depending on the service'''
        if self.request.get('service'):
            service = self.request.get('service')
            logging.debug('authenticating new %s user' % service)
            if service == 'google':
                namespace_manager.set_namespace('google')
                user = users.get_current_user()
                user = user.email()
            elif service == 'twitter':
                namespace_manager.set_namespace('twitter')
                # twitter_user_id = ''
            self.request_oauth_token()
        elif self.request.get('service_authenticated'):
            service = self.request.get('service_authenticated')
            # get the access token for the user
            namespace_manager.set_namespace(service)
            self.get_oauth_access_token()
            logging.debug('redirecting to albums')
            # reset namespace
            namespace_manager.set_namespace('')
            self.redirect('/')

    def request_oauth_token(self):
        logging.debug('requesting oauth token')
        service = namespace_manager.get_namespace()
        creds = OAuthConsumer.get()
        # ask google for request token to begin authentication
        # Create your consumer with the proper key/secret.
        consumer = oauth.Consumer(key = creds.consumer_key, secret = creds.consumer_secret)
        # Request token URL for Google
        request_token_url = self.request_token_url[service]
        # Create our client
        client = oauth.Client(consumer)
        # set any necessary parameters for the service being authorized
        if service == 'google':        
            body = 'scope=%s&oauth_callback=%s' % (
                'https://picasaweb.google.com/data/', 
                'http://fotoprojo.appspot.com/authenticate?service_authenticated=google')
        elif service == 'twitter':
            body = ''
        # make the request
        response, content = client.request(request_token_url, 'POST', body=body)
        request_token = dict(cgi.parse_qsl(content))
        
        if response['status'] == '200':
            logging.debug('successfully got oauth request token')
            OAuthCredentials.set_secret(request_token['oauth_token_secret'])
            # send user to the service's authentication page
            authorize_url = self.authorize_url[service]
            url = '%s?oauth_token=%s' % (
                authorize_url, 
                request_token['oauth_token'])
            self.redirect(url)
        else:
            logging.debug('something went wrong getting the request token:')
            logging.debug(response)
            logging.debug(content)

    def get_oauth_access_token(self):
        logging.debug('authenticating oauth access token')
        service = namespace_manager.get_namespace()
        creds = OAuthConsumer.get() # includes temporary token_secret
        creds.token = self.request.get('oauth_token')
        access_token_url = self.access_token_url[service]
        # create request information
        token = oauth.Token(key = creds.token, secret = creds.token_secret) # use the new oauth_code
        consumer = oauth.Consumer(key = creds.consumer_key, secret = creds.consumer_secret)
        token.set_verifier(self.request.get('oauth_verifier'))
        client = oauth.Client(consumer, token)
        # make the request
        response, content = client.request(access_token_url, 'GET')
        if response['status'] == '200':
            logging.debug('successfully got oauth access token')
            access_token = dict( cgi.parse_qsl(content) )
            OAuthCredentials.set(access_token)
            # set any cookies, if appropriate
            if service == 'twitter':
                self.response.headers.add_header(
                    'Set-Cookie', 'twitter_user_id=%s' % access_token['user_id'])                
            self.redirect('/')
        else:
            logging.debug('something went wrong with getting the access code')
            logging.debug(response)
            logging.debug(content)

class OAuthCredentials():
    '''has both the user and consumer information'''

    def __init__(self, user):
        # get user's oauth credentials from the db
        # redirect if they're not authenticated
        oauth_user = OAuthUser.get(user)
        oauth_consumer = OAuthConsumer.get()
        self.token = oauth_user.token
        self.token_secret = oauth_user.token_secret
        self.consumer_key = oauth_consumer.consumer_key
        self.consumer_secret = oauth_consumer.consumer_secret
    
    @classmethod
    def set(cls, new_creds):
        '''save the new credentials from oauth response'''
        # set the service to the current namespace to find credentials
        service = namespace_manager.get_namespace()
        # determine now to search for the user
        # google authentication uses email address
        # twitter uses the twitter user_id
        if service == 'google':
            user = users.get_current_user()
            user = user.email()
        if service == 'twitter':
            user = new_creds['user_id']
        # save the new user
        logging.debug('saving new ' + service + ' user: ' + user)
        logging.debug(new_creds)
        new_user = OAuthUser(
            user = user,
            token = new_creds['oauth_token'],
            token_secret = new_creds['oauth_token_secret'])
        # update credentials
        new_user.put()
        
    @classmethod
    def set_secret(cls, secret):
        '''save the temp oauth secret for authentication'''
        query = db.GqlQuery('SELECT * FROM OAuthConsumer')
        creds = query.get()
        namespace_manager.set_namespace('')
        creds.token_secret = secret
        creds.put()

class OAuthUser(db.Model):
    '''the oauth credentials for an authenticated user'''
    user = db.StringProperty()
    token = db.StringProperty()
    token_secret = db.StringProperty()
    
    @classmethod
    def get(cls, user):
        query = OAuthUser.all()
        query.filter('user =', user)
        creds = query.get()
        return OAuthUser(
            user = creds.user,
            token = creds.token,
            token_secret = creds.token_secret)
    
class OAuthConsumer(db.Model):
    '''the oauth consumer information'''
    token_secret = db.StringProperty()
    consumer_key = db.StringProperty()
    consumer_secret = db.StringProperty()
    
    @classmethod
    def get(cls):
        '''get the oauth consumer credentials from the db'''
        query = OAuthConsumer.all()
        creds = query.get()
        return OAuthConsumer(
            token_secret = creds.token_secret, 
		    consumer_key = creds.consumer_key, 
		    consumer_secret = creds.consumer_secret)