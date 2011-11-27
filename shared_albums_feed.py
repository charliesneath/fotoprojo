class SharedAlbum(db.Model):
    shared_with_twitter_user_id = db.StringProperty()
    album_id = db.StringProperty()
    owner = db.StringProperty()
    
    @classmethod
    def get():
        query = SharedAlbum.all()
        album = query.get()
        return SharedAlbum(
            token_secret = album.token_secret, 
    	    consumer_key = album.consumer_key, 
    	    consumer_secret = album.consumer_secret)

class SharedAlbumFeed(webapp.RequestHandler):
    '''feed of all albums shared with current user'''
    def get(self):
        # get all the albums shared with the current user
        all_shared_albums = SharedAlbum.get()
        shared_albums_by_owner = {}
        # build array of albums by owner
        for album in all_shared_albums:
            if not album.owner in shared_albums_by_owner:
                shared_albums_by_owner[album.owner] = []
            shared_albums_by_owner[album.owner].append(album)
        #make an API call for each owner who has shared albums with current user
        for owner, shared_albums in shared_albums_by_owner, iteritems():
            album_ids_to_filter = []
            for album in shared_albums:
                # add album_id to list of id's to filter API call
                album_ids_to_filter.append(album.album_id)
            url = self.build_request_url(owner, album_ids_to_filter)
            namespace_manager.set_namespace('google')
            creds = auth.OAuthCredentials(owner)
            namespace_manager.set_namespace('')
            token = oauth.Token(key = creds.token, secret = creds.token_secret)
            consumer = oauth.Consumer(key = creds.consumer_key, secret = creds.consumer_secret)
            client = oauth.Client(consumer, token)
            # make the API call
            response, content = client.request(url, 'GET')
            if response['status'] == '200':
                logging.debug('album feed retrieved successfully')
                data = {}
                data['albums'][owner] = []
                data['albums'][owner] = self.parse_album_feed(content)
        # after finding all of the photos by user
        data['logout_url'] = users.create_logout_url('/')
        data['twitter'] = twitter.screen_name()
        path = os.path.join(os.path.dirname(__file__), 'html/albums.html')
        self.response.out.write(template.render(path, data))
    
    def build_request_url(self, owner, album_ids_to_filter):
        # create filter by album_id
        album_id_filter = 'id[%s]' % album_ids_to_filter
        # create the main filter
        fields = 'fields=entry(%s,%s,%s,%s,%s,%s)' % (
            album_id_filter,
            'media:group/media:title',
            'media:group/media:description',
            'gphoto:location',
            'gphoto:timestamp',
            'link[@rel="alternate"]')
        url = 'https://picasaweb.google.com/data/feed/api/user/%s?%s&%s' % (
            owner,
            'alt=json',
            fields)
        return url
        
    def parse_album_feed(self, content):
        '''parse the album feed to create album objects'''
        album_feed = simplejson.loads(content)
        albums = []
        for album_info in album_feed['feed']['entry']:
            album = picasa_album.Picasa_Album(album_info)
            albums[album.year][album.month].append(album)
        albums = self.sort(albums)
        return albums

    def sort(self, albums):
        '''sorts the array of albums into ordered lists'''
        # create ordered list of months
        for year, months in albums.iteritems():
        	sorted_month_keys = sorted(months.keys(), reverse = True)
        	logging.debug(year)
        	logging.debug(sorted_month_keys)
        	sorted_month_list = []
        	for month in sorted_month_keys:
        		sorted_month_list.append(albums[year][month])
        	logging.debug(sorted_month_list)
        	# set the year to this list
        	albums[year] = sorted_month_list

        # create ordered list of years
        sorted_year_keys = sorted(albums.keys(), reverse = True)
        logging.debug(sorted_year_keys)
        for year in sorted_year_keys:
        	sorted_years_list = []
        	sorted_years_list.append(albums[year])
        logging.debug(sorted_years_list)

        # set the albums array to the newly sorted array
        albums = sorted_years_list
        return albums
    