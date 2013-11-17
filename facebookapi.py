import requests
import json

requests = requests.session()


class FacebookApi():
    def __init__(self):
        pass

    def fql(self, fql, token, args=None):
        if not args:
            args = {}

        args["query"], args["format"], args["access_token"] = fql, "json", token

        url = "https://api.facebook.com/method/fql.query"

        r = requests.get(url, params=args)
        return json.loads(r.content)

    def call(self, call, args=None):
        url = "https://graph.facebook.com/{0}".format(call)
        r = requests.get(url, params=args)
        return json.loads(r.content)
