Brid.gy ![Brid.gy](https://raw.github.com/snarfed/bridgy/master/static/bridgy_logo_128.jpg)
===

Got a web site? Post links to it on social networks? Wish
[comments/replies](http://indiewebcamp.com/comment),
[likes](http://indiewebcamp.com/like), and
[reshares](http://indiewebcamp.com/repost) showed up on your site too? Brid.gy
copies them back for you.

http://brid.gy/

Brid.gy uses [webmentions](http://www.webmention.org/), which are a part of the
[IndieWeb](http://indiewebcamp.com/) ecosystem, so your site will need to accept
webmentions for Brid.gy to work with it. Check out some of the
[existing implementations](http://indiewebcamp.com/webmention#Implementations)!

License: This project is placed in the public domain.


Development
---
All dependencies are in git submodules. Be sure to run
`git submodule init; git submodule update` after you clone the repo.

The tests require the App Engine SDK and python-mox.


Related work
---
* http://webmention.io/
* https://github.com/vrypan/webmention-tools
* http://indiewebcamp.com/original-post-discovery
* http://indiewebcamp.com/permashortcitation
* http://indiewebcamp.com/Twitter#Why_permashortcitation_instead_of_a_link


TODO
---

* BackgroundThreadLimitReachedError
  * looks like the limit may be 10 started per request. the exception happens
  before liveink is connected, but he still connects eventually and handles
  events.
  * try max_concurrent_requests in backends.yaml! jon says this may be it. per
  instance or something.
  https://developers.google.com/appengine/docs/go/config/backends?hl=en#Go_Backends_definitions
  http://code.google.com/p/googleappengine/issues/detail?id=7927
  https://groups.google.com/d/msg/google-appengine/bvzpnoSmFkY/kLarB9sEkZoJ
doesn't work in dev_appserver, but maybe prod?
  http://stackoverflow.com/questions/4983808/task-scheduling-in-appengine-dev-appserver-py
  devappserver2 is hard-coded to max 10 background threads as of 1.8.8.
  http://code.google.com/p/googleappengine/source/browse/trunk/python/google/appengine/tools/devappserver2/instance.py?r=404#449
  http://code.google.com/p/googleappengine/source/browse/trunk/python/google/appengine/tools/devappserver2/python_runtime.py?r=404#61
  http://code.google.com/p/googleappengine/source/browse/trunk/python/google/appengine/tools/devappserver2/go_runtime.py?r=404#99
  http://code.google.com/p/googleappengine/source/browse/trunk/python/google/appengine/tools/devappserver2/java_runtime.py?r=404#61
* also i see DeadlineExceededError on the sockets 1d after connecting them,
  regardless of whether there's been activity on the socket. happens in
  different places, so probably not socket but background thread deadline?
* check that when a background thread dies, we notice and reconnect. check
  stream.running bool in update_streams_once(), and implement on_close(). remove
  in both?
  odd, the existing code does reconnect, 1m later. is tweepy itself doing that?
  still add my own fixes though?
* same with updater thread, check that it's running
* translate/linkify media (picture) mentions in tweets.
  duplicate 'article' handling, starting at as/twitter.py:324. replace with
  empty string, since it's already an attachment?
  e.g. https://www.brid.gy/#twitter-liveink
  https://twitter.com/liveink/status/418850182042615808
  https://apigee.com/embed/console/twitter?req={%22resource%22%3A%22statuses_show%22%2C%22params%22%3A{%22query%22%3A{}%2C%22template%22%3A{%22id%22%3A%22418850182042615808%22}%2C%22headers%22%3A{}%2C%22body%22%3A{%22attachmentFormat%22%3A%22mime%22%2C%22attachmentContentDisposition%22%3A%22form-data%22}}%2C%22verb%22%3A%22get%22}
  "media": [{
    "id": 418850181618991100,
    "id_str": "418850181618991104",
    "indices": [
      48,
      70
    ],
    "media_url": "http://pbs.twimg.com/media/BdAOBWGCAAAsg-G.jpg",
    "media_url_https": "https://pbs.twimg.com/media/BdAOBWGCAAAsg-G.jpg",
    "url": "http://t.co/tCAEh0mdD3",
    "display_url": "pic.twitter.com/tCAEh0mdD3",
    "expanded_url": "http://twitter.com/liveink/status/418850182042615808/photo/1",
    "type": "photo",
    ...
    }]

* G+ tests for both bridgy and activitystreams-unofficial
* test for activitystreams-unofficial Twitter.fetch_replies()

Lower priority:

* am i storing refreshed access tokens? or re-refreshing every time?
* currently getting charged for the backend. switch to a module if it's still
  free? https://appengine.google.com/dashboard?&app_id=s~brid-gy#ae-nav-billing
  B1 backends get 9h free per day. *dynamic* modules get 28h free per day,
  manual only 8h.
  https://developers.google.com/appengine/kb/billing#free_quota_backends
  https://developers.google.com/appengine/docs/python/modules/#scaling_types
* detect updated comments and send new webmentions for them
* implement the other direction: convert incoming webmentions into API calls to
  post them as comments, etc.
* only handle public posts? (need to add privacy/audience detection to
  activitystreams-unofficial)
* clear toast messages?

Optimizations:

* cache some API calls with a short expiration, e.g. twitter mentions
* cache webmention discovery
* cache served MF2 HTML and JSON with a short expiration. ideally include the
  cache expiration in the content.
* ...and/or serve the comments (and activities?) directly from the datastore.
  drawback is that we don't get updated content.
* detect and skip non-HTML links before downloading, maybe with a HEAD request?
  e.g. https://twitter.com/snarfed_org/status/414172539837874176 links to
  https://research.microsoft.com/en-us/people/mickens/thesaddestmoment.pdf
