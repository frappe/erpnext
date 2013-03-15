# Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)
# 
# MIT License (MIT)
# 
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 

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
	import webnotes, os
	from webnotes.model.doc import Document
	from website.helpers.blog import get_blog_content
	
	host = (os.environ.get('HTTPS') and 'https://' or 'http://') + os.environ.get('HTTP_HOST')
	
	items = ''
	blog_list = webnotes.conn.sql("""\
		select page_name as name, published_on, modified, title, content from `tabBlog Post` 
		where ifnull(published,0)=1
		order by published_on desc limit 20""", as_dict=1)

	for blog in blog_list:
		blog.link = host + '/' + blog.name + '.html'
		
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
