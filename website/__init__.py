from __future__ import unicode_literals
install_docs = [
	{"doctype":"Role", "role_name":"Blogger", "name":"Blogger"},
	{"doctype":"Role", "role_name":"Website Manager", "name":"Website Manager"},
]

import webnotes

max_tickets_per_hour = 200

@webnotes.whitelist(allow_guest=True)
def send_message():
	from webnotes.model.doc import Document
	args = webnotes.form_dict
	
	d = Document('Support Ticket')
	d.subject = webnotes.form_dict.get('subject', 'Website Query')
	d.description = webnotes.form_dict.get('message')
	d.raised_by = webnotes.form_dict.get('sender')
	
	if not d.description:
		webnotes.response["message"] = 'Please write something'
		return
		
	if not d.raised_by:
		webnotes.response["message"] = 'Email Id Required'
		return
	
	# guest method, cap max writes per hour
	if webnotes.conn.sql("""select count(*) from `tabSupport Ticket`
		where TIMEDIFF(NOW(), modified) < '01:00:00'""")[0][0] > max_tickets_per_hour:
		webnotes.response["message"] = "Sorry: we believe we have received an unreasonably high number of requests of this kind. Please try later"
		return
	
	d.save()
	webnotes.response["message"] = 'Thank You'
	
def get_site_address():
	from webnotes.utils import get_request_site_address
	url = get_request_site_address()

	if not url or url=='http://localhost':
		new_url = webnotes.conn.get_value('Website Settings', 'Website Settings',
			'subdomain')
		if new_url:
			url = "http://" + new_url
			
	return url