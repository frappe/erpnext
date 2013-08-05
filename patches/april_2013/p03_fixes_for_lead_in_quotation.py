# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	webnotes.conn.sql("""update `tabQuotation` set customer_name = organization 
		where quotation_to = 'Lead' and ifnull(lead, '') != '' 
		and ifnull(organization, '') != ''""")
	
	webnotes.conn.sql("""update `tabQuotation` set customer_name = lead_name 
		where quotation_to = 'Lead' and ifnull(lead, '') != '' 
		and ifnull(organization, '') = '' and ifnull(lead_name, '') != ''""")
		
	webnotes.conn.sql("""update `tabQuotation` set contact_display = lead_name 
		where quotation_to = 'Lead' and ifnull(lead, '') != '' and ifnull(lead_name, '') != ''""")
		
	webnotes.conn.sql("""update `tabOpportunity` set contact_display = lead_name 
		where enquiry_from = 'Lead' and ifnull(lead, '') != '' and ifnull(lead_name, '') != ''""")
		
	webnotes.conn.sql("""update `tabOpportunity` opp, `tabLead` lead 
		set opp.customer_name = lead.company_name where opp.lead = lead.name""")