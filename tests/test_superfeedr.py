# coding=utf-8
"""Unit tests for superfeedr.py.
"""
from __future__ import unicode_literals
from __future__ import absolute_import

from google.cloud.ndb.key import _MAX_KEYPART_BYTES
from google.cloud.ndb._datastore_types import _MAX_STRING_LENGTH
from mox3 import mox
from oauth_dropins.webutil.util import json_dumps, json_loads
import webapp2

import appengine_config
from models import BlogPost
import superfeedr
from . import testutil


class FakeNotifyHandler(superfeedr.NotifyHandler):
  SOURCE_CLS = testutil.FakeSource

fake_app = webapp2.WSGIApplication([('/notify/(.+)', FakeNotifyHandler)], debug=True)


class SuperfeedrTest(testutil.HandlerTest):

  def setUp(self):
    super(SuperfeedrTest, self).setUp()
    self.source = testutil.FakeSource(id='foo.com', domains=['foo.com'],
                                      features=['webmention'])
    self.source.put()
    self.item = {'id': 'A', 'content': 'B'}
    self.feed = json_dumps({'items': [self.item]})

  def assert_blogposts(self, expected):
    got = list(BlogPost.query())
    self.assert_entities_equal(expected, got, ignore=('created', 'updated'))

  def test_subscribe(self):
    expected = {
      'hub.mode': 'subscribe',
      'hub.topic': 'fake feed url',
      'hub.callback': 'http://localhost/fake/notify/foo.com',
      'format': 'json',
      'retrieve': 'true',
      }
    item_a = {'permalinkUrl': 'A', 'content': 'a http://a.com a'}
    item_b = {'permalinkUrl': 'B', 'summary': 'b http://b.com b'}
    feed = json_dumps({'items': [item_a, {}, item_b]})
    self.expect_requests_post(superfeedr.PUSH_API_URL, feed,
                              data=expected, auth=mox.IgnoreArg())

    post_a = BlogPost(id='A', source=self.source.key, feed_item=item_a,
                      unsent=['http://a.com/'])
    post_b = BlogPost(id='B', source=self.source.key, feed_item=item_b,
                      unsent=['http://b.com/'])
    self.expect_task('propagate-blogpost', key=post_a)
    self.expect_task('propagate-blogpost', key=post_b)
    self.mox.ReplayAll()

    superfeedr.subscribe(self.source, self.handler)
    self.assert_blogposts([post_a, post_b])

  def test_handle_feed(self):
    item_a = {'permalinkUrl': 'A',
              'content': 'a http://a.com http://foo.com/self/link b'}
    post_a = BlogPost(id='A', source=self.source.key, feed_item=item_a,
                      # self link should be discarded
                      unsent=['http://a.com/'])
    self.expect_task('propagate-blogpost', key=post_a)
    self.mox.ReplayAll()

    superfeedr.handle_feed(json_dumps({'items': [item_a]}), self.source)
    self.assert_blogposts([post_a])

  def test_handle_feed_no_items(self):
    superfeedr.handle_feed('{}', self.source)
    self.assert_blogposts([])

  def test_handle_feed_disabled_source(self):
    self.source.status = 'disabled'
    self.source.put()
    superfeedr.handle_feed(self.feed, self.source)
    self.assert_blogposts([])

  def test_handle_feed_source_missing_webmention_feature(self):
    self.source.features = ['listen']
    self.source.put()
    superfeedr.handle_feed(self.feed, self.source)
    self.assert_blogposts([])

  def test_handle_feed_allows_bridgy_publish_links(self):
    item = {'permalinkUrl': 'A', 'content': 'a https://brid.gy/publish/twitter b'}
    self.expect_task('propagate-blogpost', key=BlogPost(id='A'))
    self.mox.ReplayAll()

    superfeedr.handle_feed(json_dumps({'items': [item]}), self.source)
    self.assert_equals(['https://brid.gy/publish/twitter'],
                       BlogPost.get_by_id('A').unsent)

  def test_handle_feed_unwraps_t_umblr_com_links(self):
    item = {
      'permalinkUrl': 'A',
      'id': 'A',
      'content': 'x <a href="http://t.umblr.com/redirect?z=http%3A%2F%2Fwrap%2Fped&amp;t=YmZkMzQy..."></a> y',
    }
    post = BlogPost(id='A', source=self.source.key, feed_item=item,
                    unsent=['http://wrap/ped'])
    self.expect_task('propagate-blogpost', key=post)
    self.mox.ReplayAll()

    superfeedr.handle_feed(json_dumps({'items': [item]}), self.source)
    self.assert_blogposts([post])

  def test_handle_feed_cleans_links(self):
    item = {
      'permalinkUrl': 'A',
      'id': 'A',
      'content': 'x <a href="http://abc?source=rss----12b80d28f892---4',
    }
    post = BlogPost(id='A', source=self.source.key, feed_item=item,
                    unsent=['http://abc/'])
    self.expect_task('propagate-blogpost', key=post)
    self.mox.ReplayAll()

    superfeedr.handle_feed(json_dumps({'items': [item]}), self.source)
    self.assert_blogposts([post])

  def test_notify_handler(self):
    item = {'id': 'X', 'content': 'a http://x/y z'}
    post = BlogPost(id='X', source=self.source.key, feed_item=item,
                    unsent=['http://x/y'])
    self.expect_task('propagate-blogpost', key=post)
    self.mox.ReplayAll()

    self.feed = json_dumps({'items': [item]})
    resp = fake_app.get_response('/notify/foo.com', method='POST', text=self.feed)

    self.assertEqual(200, resp.status_int)
    self.assert_blogposts([post])

  def test_notify_url_too_long(self):
    item = {'id': 'X' * (_MAX_KEYPART_BYTES + 1), 'content': 'a http://x/y z'}
    self.feed = json_dumps({'items': [item]})
    resp = fake_app.get_response('/notify/foo.com', method='POST', text=self.feed)

    self.assertEqual(200, resp.status_int)
    self.assert_blogposts([BlogPost(id='X' * _MAX_KEYPART_BYTES,
                                    source=self.source.key, feed_item=item,
                                    failed=['http://x/y'], status='complete')])

  def test_notify_link_too_long(self):
    too_long = 'http://a/' + 'b' * _MAX_STRING_LENGTH
    item = {'id': 'X', 'content': 'a http://x/y %s z' % too_long}
    post = BlogPost(id='X', source=self.source.key, feed_item=item,
                    unsent=['http://x/y'], status='new')
    self.expect_task('propagate-blogpost', key=post)
    self.mox.ReplayAll()

    self.feed = json_dumps({'items': [item]})
    resp = fake_app.get_response('/notify/foo.com', method='POST', text=self.feed)

    self.assertEqual(200, resp.status_int)
    self.assert_blogposts([post])

  def test_notify_utf8(self):
    """Check that we handle unicode chars in content ok, including logging."""
    self.feed = '{"items": [{"id": "X", "content": "a ☕ z"}]}'.encode('utf-8')
    resp = fake_app.get_response('/notify/foo.com', method='POST', text=self.feed)

    self.assertEqual(200, resp.status_int)
    self.assert_blogposts([BlogPost(id='X', source=self.source.key,
                                    feed_item={'id': 'X', 'content': 'a ☕ z'},
                                    status='complete')])
