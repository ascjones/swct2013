# -*- coding: utf-8 -*-

import json
import datetime
from collections import defaultdict

import os
import os.path
import requests

import oauth
import facebookapi

from flask import Flask, request, render_template, url_for, jsonify

FB_APP_ID = os.environ.get('FACEBOOK_APP_ID')
app_url = 'https://graph.facebook.com/{0}'.format(FB_APP_ID)
FB_APP_NAME = json.loads(requests.get(app_url).content).get('name')
FB_APP_SECRET = os.environ.get('FACEBOOK_SECRET')


app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_object('conf.Config')

fb = facebookapi.FacebookApi()


def get_home():
    return 'https://' + request.host + '/'


def get_status_updates_per_hour(access_token, user_id):

    statuses = fb.fql(
        "select time, message from status where uid = {}".format(user_id), access_token)
    hours = [datetime.datetime.fromtimestamp(int(s['time'])).hour for s in statuses]
    res = defaultdict(int)
    for h in range(0, 23, 1):
        res[h] = 0
    for h in hours:
        res[h] += 1
    return res.values()


@app.route('/', methods=['GET', 'POST'])
def index():
    # print get_home()

    fb_oauth = oauth.FacebookOAuth(app, get_home())

    access_token = fb_oauth.get_token(request, FB_APP_ID, FB_APP_SECRET)
    channel_url = url_for('get_channel', _external=True)
    channel_url = channel_url.replace('http:', '').replace('https:', '')

    if access_token:

        me = fb.call('me', args={'access_token': access_token})
        fb_app = fb.call(FB_APP_ID, args={'access_token': access_token})
        likes = fb.call('me/likes', args={'access_token': access_token, 'limit': 4})
        friends = fb.call('me/friends', args={'access_token': access_token, 'limit': 10})

        redir = get_home() + 'close/'
        POST_TO_WALL = ("https://www.facebook.com/dialog/feed?redirect_uri=%s&"
                        "display=popup&app_id=%s" % (redir, FB_APP_ID))

        status_updates_per_hour = get_status_updates_per_hour(access_token, 'me()')
        status_updates_per_hour = ','.join([str(x) for x in status_updates_per_hour])

        SEND_TO = ('https://www.facebook.com/dialog/send?'
                   'redirect_uri=%s&display=popup&app_id=%s&link=%s'
                   % (redir, FB_APP_ID, get_home()))

        url = request.url

        return render_template(
            'index.html', app_id=FB_APP_ID, token=access_token[0], likes=likes,
            friends=friends, status_updates_per_hour=status_updates_per_hour, app=fb_app,
            me=me, POST_TO_WALL=POST_TO_WALL, SEND_TO=SEND_TO, url=url,
            channel_url=channel_url, name=FB_APP_NAME)
    else:
        return render_template('login.html', app_id=FB_APP_ID, token=access_token, url=request.url, channel_url=channel_url, name=FB_APP_NAME)


@app.route('/friend/<friend_id>')
def get_friend(friend_id):
    access_token = request.args.get('access_token')

    if access_token:
        status_updates_per_hour = get_status_updates_per_hour(access_token, friend_id)
        return jsonify({'statuses': status_updates_per_hour})
    else:
        raise Exception('Not authenticated')



@app.route('/channel.html', methods=['GET', 'POST'])
def get_channel():
    return render_template('channel.html')


@app.route('/close/', methods=['GET', 'POST'])
def close():
    return render_template('close.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5555))
    if app.config.get('FB_APP_ID') and app.config.get('FB_APP_SECRET'):
        app.run(host='0.0.0.0', port=port)
    else:
        print 'Cannot start application without Facebook App Id and Secret set'
