# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("setup", "doctype", "email_digest")
	
	from webnotes.profile import get_system_managers
	system_managers = get_system_managers(only_name=True)
	if not system_managers: 
		return
	
	# no default company
	company = webnotes.conn.sql_list("select name from `tabCompany`")
	if company:
		company = company[0]
	if not company:
		return
	
	# scheduler errors digest
	edigest = webnotes.new_bean("Email Digest")
	edigest.doc.fields.update({
		"name": "Scheduler Errors",
		"company": company,
		"frequency": "Daily",
		"enabled": 1,
		"recipient_list": "\n".join(system_managers),
		"scheduler_errors": 1
	})
	edigest.insert()
