import base64
import urllib
import requests
import hmac
import hashlib
import json
from base64 import urlsafe_b64decode, urlsafe_b64encode

requests = requests.session()


class FacebookOAuth():
    def __init__(self, app, home_url):
        self.app = app
        self.home_url = home_url

    def oauth_login_url(self):
        fb_login_uri = ("https://www.facebook.com/dialog/oauth"
                        "?client_id=%s&redirect_uri=%s" %
                        (self.app.config['FB_APP_ID'], self.home_url))

        if self.app.config['FBAPI_SCOPE']:
            fb_login_uri += "&scope=%s" % ",".join(self.app.config['FBAPI_SCOPE'])
        return fb_login_uri

    def base64_url_encode(self, data):
        return base64.urlsafe_b64encode(data).rstrip('=')

    def fbapi_get_string(self, path,
                         domain=u'graph', params=None, access_token=None,
                         encode_func=urllib.urlencode):
        """Make an API call"""

        if not params:
            params = {}
        params[u'method'] = u'GET'
        if access_token:
            params[u'access_token'] = access_token

        for k, v in params.iteritems():
            if hasattr(v, 'encode'):
                params[k] = v.encode('utf-8')

        url = u'https://' + domain + u'.facebook.com' + path
        params_encoded = encode_func(params)
        url = url + params_encoded
        result = requests.get(url).content

        return result

    def fbapi_auth(self, code):
        params = {'client_id': self.app.config['FB_APP_ID'],
                  'redirect_uri': self.home_url,
                  'client_secret': self.app.config['FB_APP_SECRET'],
                  'code': code}

        def simple_dict_serialisation(params):
            return "&".join(map(lambda k: "%s=%s" % (k, params[k]), params.keys()))

        result = self.fbapi_get_string(path=u"/oauth/access_token?", params=params,
                                       encode_func=simple_dict_serialisation)
        pairs = result.split("&", 1)
        result_dict = {}
        for pair in pairs:
            (key, value) = pair.split("=")
            result_dict[key] = value
        return result_dict["access_token"], result_dict["expires"]

    def get_application_access_token(self, id):
        token = self.fbapi_get_string(
            path=u"/oauth/access_token",
            params=dict(grant_type=u'client_credentials', client_id=id,
                        client_secret=self.app.config['FB_APP_SECRET']),
            domain=u'graph')

        token = token.split('=')[-1]
        if not str(id) in token:
            print 'Token mismatch: %s not in %s' % (id, token)
        return token

    def get_token(self, request, app_id, app_secret):

        if request.args.get('code', None):
            return self.fbapi_auth(request.args.get('code'))[0]

        cookie_key = 'fbsr_{0}'.format(app_id)

        if cookie_key in request.cookies:

            c = request.cookies.get(cookie_key)
            encoded_data = c.split('.', 2)

            sig = encoded_data[0]
            data = json.loads(urlsafe_b64decode(str(encoded_data[1]) +
                (64-len(encoded_data[1])%64)*"="))

            if not data['algorithm'].upper() == 'HMAC-SHA256':
                raise ValueError('unknown algorithm {0}'.format(data['algorithm']))

            h = hmac.new(app_secret, digestmod=hashlib.sha256)
            h.update(encoded_data[1])
            expected_sig = urlsafe_b64encode(h.digest()).replace('=', '')

            if sig != expected_sig:
                raise ValueError('bad signature')

            code = data['code']

            params = {
                'client_id': app_id,
                'client_secret': app_secret,
                'redirect_uri': '',
                'code': data['code']
            }

            from urlparse import parse_qs
            r = requests.get('https://graph.facebook.com/oauth/access_token', params=params)
            token = parse_qs(r.content).get('access_token')

            return token