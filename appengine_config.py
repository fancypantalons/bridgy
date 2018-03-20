"""Bridgy App Engine config.
"""
import logging
import os

# Load packages from virtualenv
# https://cloud.google.com/appengine/docs/python/tools/libraries27#vendoring
from google.appengine.ext import vendor
try:
  vendor.add('local')
except Exception as e_local:
  virtual_env = os.getenv('VIRTUAL_ENV')
  try:
    vendor.add(virtual_env)
  except Exception as e_env:
    logging.warning("Couldn't set up App Engine vendor for local: %s\n  or %s: %s",
                    e_local, virtual_env, e_env)
    raise

from granary.appengine_config import *

DISQUS_ACCESS_TOKEN = read('disqus_access_token')
DISQUS_API_KEY = read('disqus_api_key')
DISQUS_API_SECRET = read('disqus_api_secret')
FACEBOOK_TEST_USER_TOKEN = (os.getenv('FACEBOOK_TEST_USER_TOKEN') or
                            read('facebook_test_user_access_token'))
SUPERFEEDR_TOKEN = read('superfeedr_token')
SUPERFEEDR_USERNAME = read('superfeedr_username')

# Make requests and urllib3 play nice with App Engine.
# https://github.com/snarfed/bridgy/issues/396
# http://stackoverflow.com/questions/34574740
from requests_toolbelt.adapters import appengine
appengine.monkeypatch()

# Wrap webutil.util.tag_uri and hard-code the year to 2013.
#
# Needed because I originally generated tag URIs with the current year, which
# resulted in different URIs for the same objects when the year changed. :/
from oauth_dropins.webutil import util
util._orig_tag_uri = util.tag_uri
util.tag_uri = lambda domain, name: util._orig_tag_uri(domain, name, year=2013)

# I used a namespace for a while when I had both versions deployed, but not any
# more; I cleared out the old v1 datastore entities.
# Called only if the current namespace is not set.
# from google.appengine.api import namespace_manager
# def namespace_manager_default_namespace_for_request():
#   return 'webmention-dev'

# Suppress warnings. These are duplicated in oauth-dropins and bridgy; keep them
# in sync!
import warnings
warnings.filterwarnings('ignore', module='bs4',
                        message='No parser was explicitly specified')
warnings.filterwarnings('ignore', message='urllib3 is using URLFetch')
warnings.filterwarnings('ignore',
                        message='URLFetch does not support granular timeout')


def webapp_add_wsgi_middleware(app):
  # # uncomment for app stats
  # appstats_CALC_RPC_COSTS = True
  # from google.appengine.ext.appstats import recording
  # app = recording.appstats_wsgi_middleware(app)

  # # uncomment for instance_info concurrent requests recording
  # from oauth_dropins.webutil import instance_info
  # app = instance_info.concurrent_requests_wsgi_middleware(app)

  return app

# monkey-patch WsgiRequest to allow unicode header values.
from google.appengine.runtime.wsgi import WsgiRequest
orig_response = WsgiRequest._StartResponse

def unicode_start_response(self, status, response_headers, exc_info=None):
  # {str(name): value.encode('utf-8')
  return orig_response(self, status, util.encode(response_headers), exc_info)

WsgiRequest._StartResponse = unicode_start_response
