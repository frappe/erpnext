# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

@webnotes.whitelist(allow_guest=True)
def send_message(subject="Website Query", message="", sender="", status="Open"):
	from webnotes.templates.pages.contact import send_message as website_send_message
	
	if not website_send_message(subject, message, sender):
		return
		
	if subject=="Support":
		# create support ticket
		from erpnext.support.doctype.support_ticket.get_support_mails import add_support_communication
		add_support_communication(subject, message, sender, mail=None)
	else:
		# make lead / communication
		from erpnext.selling.doctype.lead.get_leads import add_sales_communication
		add_sales_communication(subject or "Website Query", message, sender, sender, 
			mail=None, status=status)
	