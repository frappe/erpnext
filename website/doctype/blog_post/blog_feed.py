# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt 

from __future__ import unicode_literals
"""
Generate RSS feed for blog
"""

rss = u"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
        <title>%(title)s</title>
        <description>%(description)s</description>
        <link>%(link)s</link>
        <lastBuildDate>%(modified)s</lastBuildDate>
        <pubDate>%(modified)s</pubDate>
        <ttl>1800</ttl>
		%(items)s
</channel>
</rss>"""

rss_item = u"""
<item>
        <title>%(title)s</title>
        <description>%(content)s</description>
        <link>%(link)s</link>
        <guid>%(name)s</guid>
        <pubDate>%(published_on)s</pubDate>
</item>"""

def generate():
	"""generate rss feed"""
	import os, urllib
	import webnotes
	from webnotes.model.doc import Document
	from webnotes.utils import escape_html
	
	host = (os.environ.get('HTTPS') and 'https://' or 'http://') + os.environ.get('HTTP_HOST')
	
	items = ''
	blog_list = webnotes.conn.sql("""\
		select page_name as name, published_on, modified, title, content from `tabBlog Post` 
		where ifnull(published,0)=1
		order by published_on desc limit 20""", as_dict=1)

	for blog in blog_list:
		blog.link = urllib.quote(host + '/' + blog.name + '.html')
		blog.content = escape_html(blog.content or "")
		
		items += rss_item % blog

	modified = max((blog['modified'] for blog in blog_list))
		
	ws = Document('Website Settings', 'Website Settings')
	return (rss % {
				'title': ws.title_prefix,
				'description': ws.description or (ws.title_prefix + ' Blog'),
				'modified': modified,
				'items': items,
				'link': host + '/blog.html'
			}).encode('utf-8', 'ignore')
