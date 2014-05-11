# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

# reason field

def execute():
	change_map = {
		"Lead": [
			["Lead Lost", "Lead"],
			["Not interested", "Do Not Contact"],
			["Opportunity Made", "Opportunity"],
			["Contacted", "Replied"],
			["Attempted to Contact", "Replied"],
			["Contact in Future", "Interested"],
		],
		"Opportunity": [
			["Quotation Sent", "Quotation"],
			["Order Confirmed", "Quotation"],
			["Opportunity Lost", "Lost"],
		],
		"Quotation": [
			["Order Confirmed", "Ordered"],
			["Order Lost", "Lost"]
		],
		"Support Ticket": [
			["Waiting for Customer", "Replied"],
			["To Reply", "Open"],
		]
	}
	
	for dt, opts in change_map.items():
		for status in opts:
			webnotes.conn.sql("""update `tab%s` set status=%s where status=%s""" % \
				(dt, "%s", "%s"), (status[1], status[0]))
				
	for dt in ["Lead", "Opportunity"]:
		for name in webnotes.conn.sql_list("""select name from `tab%s`""" % dt):
			bean = webnotes.bean(dt, name)
			before_status = bean.doc.status
			bean.get_controller().set_status()
			
			if bean.doc.status != before_status:
				webnotes.conn.sql("""update `tab%s` set status=%s where name=%s""" % (dt, "%s", "%s"),
					(bean.doc.status, name))
