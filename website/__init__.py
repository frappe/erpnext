from __future__ import unicode_literals
install_docs = [
	{"doctype":"Role", "role_name":"Blogger", "name":"Blogger"},
	{"doctype":"Role", "role_name":"Website Manager", "name":"Website Manager"},
]

import webnotes

	
def get_site_address():
	from webnotes.utils import get_request_site_address
	url = get_request_site_address()

	if not url or url=='http://localhost':
		new_url = webnotes.conn.get_value('Website Settings', 'Website Settings',
			'subdomain')
		if new_url:
			url = "http://" + new_url
			
	return url