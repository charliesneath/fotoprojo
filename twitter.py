def get_twitter_screen_name():
    # if there's a cookie
    cj = {}
    twitter_user = twitter_auth.Twitter_User()
    cookies = self.request.headers['Cookie']
    # get each cookie
    cookies = cookies.split(';')
    for cookie in cookies:
        # get each cooke value  
        cookie = cookie.split('=')
        cookie[0] = cookie[0].strip()
        cookie[1] = cookie[1].strip()
        cj[cookie[0]] = cookie[1]
    # get twitter handle from the user_id if a cookie is found
    try:
        if cj['twitter_user_id']:
            twitter_user.get(cj['twitter_user_id'])
            twitter_info = {}
            twitter_info['screen_name'] = twitter_user.screen_name
            return twitter_info
    except KeyError, e:
        logging.debug(e.message)
        logging.debug('cooke info not found, twitter user not authorized')
        return
