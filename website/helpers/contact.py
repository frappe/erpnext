# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes
from webnotes.utils import now

max_communications_per_hour = 300

@webnotes.whitelist(allow_guest=True)
def send_message(subject="Website Query", message="", sender="", status="Open"):
	if not message:
		webnotes.response["message"] = 'Please write something'
		return
		
	if not sender:
		webnotes.response["message"] = 'Email Id Required'
		return

	# make lead / communication
	from selling.doctype.lead.get_leads import add_sales_communication
	message = add_sales_communication(subject or "Website Query", message, sender, sender, 
		mail=None, status=status)
	
	# guest method, cap max writes per hour
	if webnotes.conn.sql("""select count(*) from `tabCommunication`
		where TIMEDIFF(%s, modified) < '01:00:00'""", now())[0][0] > max_communications_per_hour:
		webnotes.response["message"] = "Sorry: we believe we have received an unreasonably high number of requests of this kind. Please try later"
		return
	
	webnotes.response.status = "okay"
