# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("utilities", "doctype", "address")
	
	webnotes.conn.auto_commit_on_many_writes = True
	
	for lead in webnotes.conn.sql("""select name as lead, lead_name, address_line1, address_line2, city, country,
		state, pincode, status, company_name from `tabLead` where not exists 
		(select name from `tabAddress` where `tabAddress`.lead=`tabLead`.name) and 
			(ifnull(address_line1, '')!='' or ifnull(city, '')!='' or ifnull(country, '')!='' or ifnull(pincode, '')!='')""", as_dict=True):
			if set_in_customer(lead):
				continue

			create_address_for(lead)
			
	webnotes.conn.auto_commit_on_many_writes = False
			
def set_in_customer(lead):
	customer = webnotes.conn.get_value("Customer", {"lead_name": lead.lead})
	if customer:
		customer_address = webnotes.conn.sql("""select name from `tabAddress`
			where customer=%s and (address_line1=%s or address_line2=%s or pincode=%s)""", 
			(customer, lead.address_line1, lead.address_line2, lead.pincode))
		if customer_address:
			webnotes.conn.sql("""update `tabAddress` set lead=%s, lead_name=%s
				where name=%s""", (lead.lead, lead.company_name or lead.lead_name, customer_address[0][0]))
			return True
			
	return False
			
def create_address_for(lead):
	address_title = lead.company_name or lead.lead_name or lead.lead
	
	for c in ['%', "'", '"', '#', '*', '?', '`']:
		address_title = address_title.replace(c, "")
	
	if webnotes.conn.get_value("Address", address_title.strip() + "-" + "Billing"):
		address_title += " " + lead.lead 
	
	lead.update({
		"doctype": "Address", 
		"address_type": "Billing", 
		"address_title": address_title
	})
	
	del lead["company_name"]
	del lead["status"]
	
	lead_bean = webnotes.bean(lead)
	lead_bean.ignore_mandatory = True
	lead_bean.insert()