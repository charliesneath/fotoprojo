# upgrade to django 1.2
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings' 
from google.appengine.dist import use_library
use_library('django', '1.2')

# my modules
import fotoprojo_users
import auth
import picasa_entry
import twitter
import google

# GAE modules
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import urlfetch
import logging
from google.appengine.api import namespace_manager
from google.appengine.ext.webapp import template

# other python modules
import os
import datetime
import time
import urllib
from urlparse import urlparse
import cgi
import cookielib
import oauth2 as oauth
from django.utils import simplejson

class PicasaFeed(webapp.RequestHandler):
    ''''''
    def get(self):
        # if this is the link to an album
        if self.request.get('album_id'):
            feed_type = 'photos'
        else:
            feed_type = 'albums'
        namespace_manager.set_namespace('google')
        user = users.get_current_user()
        try:
            # get credentials from the db
            creds = auth.OAuthCredentials(user.email())
            logging.debug('%s is already authenticated with %s and %s' % (user.email(), creds.token, creds.token_secret))
            self.fetch_feed(feed_type, creds)
        except AttributeError, e:
            # if the user isn't authenticated
            if e.message == "'NoneType' object has no attribute 'user'":
                logging.debug('need to authenticate %s' % user.email())
                self.redirect('/authenticate?service=google')
                
    def fetch_feed(self, feed_type, creds):
        # set the oauth credentials
        user = users.get_current_user()
        logging.debug('getting albums for: %s' % user.email())
        oauth_client = auth.create_oauth_client(user.email(), 'google')
        url = self.feed_url(feed_type)
        response, content = oauth_client.request(url, 'GET')
        if response['status'] == '200':
            logging.debug('album feed retrieved successfully')
            data = {}
            if feed_type == 'albums':
                data['albums'] = self.parse_picasa_feed(feed_type, simplejson.loads(content))
                path = os.path.join(os.path.dirname(__file__), 'albums.html')
            elif feed_type == 'photos': 
                data['album'], data['photos'] = self.parse_picasa_feed(feed_type, simplejson.loads(content))
                path = os.path.join(os.path.dirname(__file__), 'photos.html')
            # data['twitter'] = twitter.get_twitter_screen_name()
            self.response.out.write(template.render(path, data))
        elif content == 'Unknown user.':
            # if user hasn't started using web albums yet
            picasa_link = '<a href="picasaweb.google.com">here</a>'
            logout_url = '<a href=\"%s\">log out</a>' % users.create_logout_url('/')
            self.response.out.write('You haven\'t create a Picasa Web account yet! Click %s to start or %s.' % (picasa_link, logout_url))
        else:
            self.response.out.write('something went wrong!!!')
            logging.debug('something went wrong!!!')
            logging.debug(content)
            logging.debug(response)
            
    def feed_url(self, feed_type):
        user = users.get_current_user()
        if feed_type == 'albums':
            fields = 'fields=entry(%s,%s,%s,%s,%s,%s)' % (
                'gphoto:id',
                'title',
                'summary',
                'gphoto:location',
                'gphoto:timestamp',
                'media:group/media:keywords')
            url = 'https://picasaweb.google.com/data/feed/api/user/%s?%s&%s&%s' % (
                user.email(),
                'alt=json',
                fields,
                'prettyprint=true')
                
        elif feed_type == 'photos':
            fields = 'fields=title,subtitle,gphoto:timestamp,gphoto:location,entry(%s,%s,%s,%s)' % (
                'gphoto:id',
                'gphoto:albumid',
                'gphoto:timestamp',
                'media:group/media:thumbnail[@url]')
            url = 'https://picasaweb.google.com/data/feed/api/user/%s/albumid/%s?%s&%s&%s&%s' % (
                user.email(),
                self.request.get('album_id'), # album id from the URL
                'alt=json',
                'thumbsize=220,512',
                fields,
                'prettyprint=true')
        
        return url
            
    def parse_picasa_feed(self, feed_type, feed): 
        # parse feed of albums
        if feed_type == 'albums':
            albums = {}
            for properties in feed['feed']['entry']:
                album = picasa_entry.PicasaEntry('albums', properties)
                # set this year if it's not set
                if not album.year in albums:
                    albums[album.year] = {}
                # then make sure the month is set, make a new list if not
                if not album.month in albums[album.year]:
                    # create new list of albums for this month
                    albums[album.year][album.month] = []
                # add the album to the list
                albums[album.year][album.month].append(album)
            albums = self.sort(albums)
            return albums
        # parse feed of photos
        elif feed_type == 'photos':
            logging.debug(feed)
            album = self.get_album_info(feed)
            photos = []
            try:
                for properties in feed['feed']['entry']:
                    photo = picasa_entry.PicasaEntry('photos', properties)
                    photos.append(photo)
                return album, photos
            except KeyError:
                # if there aren't any photos in the album
                logging.debug('There aren\'t any photos in the album.')
                return album, ''
            
    def get_album_info(self, feed):
        '''get the album info from the head of the feed'''
        album = Album()
        album.title = feed['feed']['title']['$t']
        # subtitle is the album description 
        album.description = feed['feed']['subtitle']['$t']
        # get the display date from the album's timestamp
        timestamp = int(feed['feed']['gphoto$timestamp']['$t'])/1000
        album.display_date = time.strftime('%B %e', time.localtime(timestamp))
        album.location = feed['feed']['gphoto$location']['$t']
        try:
            album.tags = self.get_tags()
        except KeyError:
            pass
        album.year = time.strftime('%Y', time.localtime(timestamp))
        album.month = time.strftime('%B', time.localtime(timestamp))
        return album
        
    def get_tags(self):
        logging.debug('getting tags for album')
        user = users.get_current_user()
        oauth_client = auth.create_oauth_client(user.email(), 'google')
        url = 'https://picasaweb.google.com/data/feed/api/user/%s/albumid/%s?prettyprint=true&alt=json&kind=tag&fields=entry(title)' % (user.email(), self.request.get('album_id'))
        response, content = oauth_client.request(url, 'GET')
        feed = simplejson.loads(content)
        tags = []
        # each tag is an entry in the feed
        try:
            for tag in feed['feed']['entry']:
                tags.append(tag['title']['$t'])
            return tags
        except KeyError:
            return
            
    def sort(self, albums):
        '''sorts the array of albums into ordered lists'''
        # create ordered list of months
        month_names = self.month_names()
        list_of_years = []
        year_keys = sorted(albums.keys(), reverse = True)
        for year in year_keys:
            # reset months list
            months_with_albums = []
            month_keys = sorted(albums[year].keys(), reverse = True)
            for month in month_keys:
                # add this month's list of albums to the list of months
                months_with_albums.append({month_names[month]: albums[year][month]})
            # add the list of months to the list of years
            list_of_years.append({year: months_with_albums})
        return list_of_years
                
    def month_names(self):
        month_names = {
            '01': 'January',
            '02': 'February',
            '03': 'March',
            '04': 'April',
            '05': 'May',
            '06': 'June',
            '07': 'July',
            '08': 'August',
            '09': 'September',
            '10': 'October',
            '11': 'November',
            '12': 'December'
        }
        return month_names
        
class Album():
    pass