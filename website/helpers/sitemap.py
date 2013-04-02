# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals
frame_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s
</urlset>"""

link_xml = """\n<url><loc>%s</loc><lastmod>%s</lastmod></url>"""

# generate the sitemap XML
def generate(domain):
	global frame_xml, link_xml
	import urllib, os
	import webnotes
	import webnotes.webutils

	# settings
	max_doctypes = 10
	max_items = 1000
	
	site_map = ''
	page_list = []
	
	if domain:
		# list of all pages in web cache
		for doctype in webnotes.webutils.page_map:
			d = webnotes.webutils.page_map[doctype];
			pages = webnotes.conn.sql("""select page_name, `modified`
				from `tab%s` where ifnull(%s,0)=1
				order by modified desc""" % (doctype, d.condition_field))
		
			for p in pages:
				page_url = os.path.join(domain, urllib.quote(p[0]))
				modified = p[1].strftime('%Y-%m-%d')
				site_map += link_xml % (page_url, modified)

		return frame_xml % site_map
