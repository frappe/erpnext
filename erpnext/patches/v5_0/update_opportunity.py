# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('crm', 'doctype', 'opportunity')
	frappe.reload_doc('crm', 'doctype', 'opportunity_item')

	# all existing opportunities were with items
	frappe.db.sql("update `tabDocType` set module = 'CRM' where name='Opportunity Item'")
	frappe.db.sql("update tabOpportunity set with_items=1, title=customer_name")
	frappe.db.sql("update `tabEmail Account` set append_to='Opportunity' where append_to='Lead'")
