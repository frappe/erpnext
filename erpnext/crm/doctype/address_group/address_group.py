# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AddressGroup(Document):

	@frappe.whitelist()
	def dynamic_state(self):
		query = frappe.db.sql("""
		Select DISTINCT tadd.gst_state from `tabAddress` tadd
		join `tabDynamic Link` dl on dl.parent = tadd.name
		where link_doctype = "Company" and link_title = '{0}'
		""".format(self.company))
		print(" +++++++++++= states +++++++++", query)
		return query

	@frappe.whitelist()
	def dynamic_address(self):
		query = frappe.db.sql("""
		Select tadd.name from `tabAddress` tadd
		join `tabDynamic Link` dl on dl.parent = tadd.name
		where dl.link_doctype = "Company" and dl.link_title = '{0}'
		and tadd.gst_state = '{1}'

		""".format(self.company,self.state))
		print(" +++++++++++= address +++++++++", query)
		return query


