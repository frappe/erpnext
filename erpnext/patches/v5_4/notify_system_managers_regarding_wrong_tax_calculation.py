# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.email import sendmail_to_system_managers
from frappe.utils import get_link_to_form

def execute():
	wrong_records = []
	for dt in ("Quotation", "Sales Order", "Delivery Note", "Sales Invoice", 
		"Purchase Order", "Purchase Receipt", "Purchase Invoice"):
			records = frappe.db.sql_list("""select name from `tab{0}` 
				where apply_discount_on = 'Net Total' and ifnull(discount_amount, 0) != 0
				and modified >= '2015-02-17' and docstatus=1""".format(dt))
		
			if records:
				records = [get_link_to_form(dt, d) for d in records]
				wrong_records.append([dt, records])
				
	if wrong_records:
		content = """Dear System Manager,

Due to an error related to Discount Amount on Net Total, tax calculation might be wrong in the following records. We did not fix the tax amount automatically because it can corrupt the entries, so we request you to check these records and amend if you found the calculation wrong.

Please check following Entries:

%s


Regards,

Administrator""" % "\n".join([(d[0] + ": " + ", ".join(d[1])) for d in wrong_records])
		try:
			sendmail_to_system_managers("[Important] [ERPNext] Tax calculation might be wrong, please check.", content)
		except:
			pass
		
		print "="*50
		print content
		print "="*50