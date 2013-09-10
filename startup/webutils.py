# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes, conf, os
from webnotes.utils import cint, cstr, encode
	
@webnotes.whitelist()
def update_profile(fullname, password=None, company_name=None, mobile_no=None, phone=None):
	from selling.utils.cart import update_party
	update_party(fullname, company_name, mobile_no, phone)
	
	from core.doctype.profile import profile
	return profile.update_profile(fullname, password)
	
def get_profile_args():
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