# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import cstr

no_cache = True
no_sitemap = True

def get_context():
	from selling.utils.cart import get_lead_or_customer
	party = get_lead_or_customer()
	if party.doctype == "Lead":
		mobile_no = party.mobile_no
		phone = party.phone
	else:
		mobile_no, phone = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user, 
			"customer": party.name}, ["mobile_no", "phone"])
		
	return {
		"company_name": cstr(party.customer_name if party.doctype == "Customer" else party.company_name),
		"mobile_no": cstr(mobile_no),
		"phone": cstr(phone)
	}
	
@webnotes.whitelist()
def update_profile(fullname, password=None, company_name=None, mobile_no=None, phone=None):
	from selling.utils.cart import update_party
	update_party(fullname, company_name, mobile_no, phone)
	
	if not fullname:
		return _("Name is required")
		
	webnotes.conn.set_value("Profile", webnotes.session.user, "first_name", fullname)
	webnotes._response.set_cookie("full_name", fullname)
	
	return _("Updated")
	