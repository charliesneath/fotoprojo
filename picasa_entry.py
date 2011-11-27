# my modules
import auth

# python modules
import time

# GAE modules
import logging
from django.utils import simplejson
from google.appengine.api import users

class PicasaEntry():
    '''an entry in a feed from the Picasa Web API'''
    
    def __init__(self, feed_type, properties):
        '''get attributes for each album in the feed'''
        user = users.get_current_user()
        timestamp = int(properties['gphoto$timestamp']['$t'])/1000
        self.display_date = time.strftime('%B %e', time.localtime(timestamp))
        
        if feed_type == 'albums':
            self.id = properties['gphoto$id']['$t']
            self.title = properties['title']['$t']
            self.description = properties['summary']['$t']
            self.location = properties['gphoto$location']['$t']
            self.link = 'http://fotoprojo.appspot.com?album_id=%s' % properties['gphoto$id']['$t']
            self.year = time.strftime('%Y', time.localtime(timestamp))
            self.month = time.strftime('%m', time.localtime(timestamp))
        
        elif feed_type == 'photos':
            self.link = 'https://picasaweb.google.com/data/media/api/user/%s/albumid/%s/photoid/%s' % (
                user.email(),
                properties['gphoto$albumid']['$t'],
                properties['gphoto$id']['$t'])
            self.thumbnail = properties['media$group']['media$thumbnail'][0]['url']
            self.preview = properties['media$group']['media$thumbnail'][1]['url']

    def get_authkey(self, album_link):
        '''parse the album's URL for the authkey'''
        try:
            album_link = urlparse(album_link)
            # create dictionary from album_link[4], the query string of the split URL
            album_link = dict(cgi.parse_qsl(album_link[4]))
            authkey = album_link['authkey']
        except:
            authkey = ''
        return authkey

    