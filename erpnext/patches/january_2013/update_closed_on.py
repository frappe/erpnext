# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("core", "doctype", "docfield")
	webnotes.reload_doc("support", "doctype", "support_ticket")
	
	# customer issue resolved_by should be Profile
	if webnotes.conn.sql("""select count(*) from `tabCustomer Issue` 
		where ifnull(resolved_by,"")!="" """)[0][0]:
		webnotes.make_property_setter({
			"doctype":"Customer Issue", 
			"fieldname": "resolved_by", 
			"property": "options",
			"value": "Sales Person"
		})
		
	def get_communication_time(support_ticket, sort_order = 'asc'):
		tmp = webnotes.conn.sql("""select creation from tabCommunication where
			support_ticket=%s order by creation %s limit 1""" % ("%s", sort_order), 
			support_ticket)
		return tmp and tmp[0][0] or None
		
	# update in support ticket
	webnotes.conn.auto_commit_on_many_writes = True
	for st in webnotes.conn.sql("""select name, modified, status from 
		`tabSupport Ticket`""", as_dict=1):
		
		webnotes.conn.sql("""update `tabSupport Ticket` set first_responded_on=%s where 
			name=%s""", (get_communication_time(st.name) or st.modified, st.name))
		if st.status=="Closed":
			webnotes.conn.sql("""update `tabSupport Ticket` set resolution_date=%s where 
				name=%s""", (get_communication_time(st.name, 'desc') or st.modified, st.name))
