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
	from webnotes.utils import nowdate

	# settings
	max_items = 1000
	count = 0
	
	site_map = ''
	if domain:
		today = nowdate()
		
		# generated pages
		for doctype, opts in webnotes.webutils.get_generators().items():
			pages = webnotes.conn.sql("""select page_name, `modified`
				from `tab%s` where ifnull(%s,0)=1
				order by modified desc""" % (doctype, opts.get("condition_field")))
		
			for p in pages:
				if count >= max_items: break
				page_url = os.path.join(domain, urllib.quote(p[0]))
				modified = p[1].strftime('%Y-%m-%d')
				site_map += link_xml % (page_url, modified)
				count += 1
				
			if count >= max_items: break
		
		# standard pages
		for page, opts in webnotes.get_config()["web"]["pages"].items():
			if "no_cache" in opts:
				continue
			
			if count >= max_items: break
			page_url = os.path.join(domain, urllib.quote(page))
			modified = today
			site_map += link_xml % (page_url, modified)
			count += 1

	return frame_xml % site_map
