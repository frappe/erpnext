# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import cint
import frappe
from frappe.model.document import Document

class TransactionDeletionLog(Document):
	def validate(self):
		max_num_of_doctypes = len(doctypes())
		if not (len(self.get("doctypes_to_be_ignored")) == max_num_of_doctypes):
			frappe.throw(__("DocTypes should not be added manually to the 'DocTypes That Won't Be Affected' table."))

	def on_submit(self):
		doctypes = frappe.get_all('Docfield', 
			filters = {
				'fieldtype': 'Link', 
				'options': 'Company'},
			fields=["parent", "fieldname"])

		ignore = ['Transaction Deletion Log', 'Opening Invoice Creation Tool', 'Chart of Accounts Importer', 'Payment Reconciliation', 'Bank Reconciliation Tool', 'Global Defaults', 'Employee Attendance Tool', 'Leave Control Panel', 'Shopping Cart Settings', 'Homepage', 'Woocommerce Settings', 'Shopify Settings', 'Amazon MWS Settings', 'QuickBooks Migrator']	
		for doctype in doctypes:
			if doctype['parent'] not in ignore:
				no_of_docs = frappe.db.count(doctype['parent'], {
							doctype['fieldname'] : self.company
						}, debug=1)
				if no_of_docs > 0:
					# populate DocTypes table
					self.append('doctypes', {
						"doctype_name" : doctype['parent'],
						"no_of_docs" : no_of_docs
					})

					# delete the docs linked with the specified company
					frappe.db.delete(doctype['parent'], {
						doctype['fieldname'] : self.company
					})

					naming_series = frappe.db.get_value('DocType', doctype['parent'], 'autoname')
					if naming_series:
						if '#' in naming_series:
							self.update_naming_series(naming_series, doctype['parent'])			


		# doctypes = frappe.get_all('Doctype',
		# 	filters={
		# 		'issingle' : 0,
		# 		'istable' : 0
		# 	})

		# for doctype in doctypes:
		# 	if doctype.name != 'Transaction Deletion Log':
		# 		doctype_fields = frappe.get_meta(doctype.name).as_dict()['fields']
		# 		for doctype_field in doctype_fields:
		# 			if doctype_field['fieldtype'] == 'Link' and doctype_field['options'] == 'Company':
		# 				no_of_docs = frappe.db.count(doctype.name, {
		# 					doctype_field['fieldname'] : self.company
		# 				})
		# 				if no_of_docs > 0:
		# 					# populate DocTypes table
		# 					self.append('doctypes', {
		# 						"doctype_name" : doctype.name,
		# 						"no_of_docs" : no_of_docs
		# 					})

		# 					# delete the docs linked with the specified company
		# 					frappe.db.delete(doctype.name, {
		# 						doctype_field['fieldname'] : self.company
		# 					})

		# 					naming_series = frappe.db.get_value('DocType', doctype.name, 'autoname')
		# 					if naming_series:
		# 						if '#' in naming_series:
		# 							self.update_naming_series(naming_series, doctype.name)
		# 				break

	def update_naming_series(self, naming_series, doctype_name):
		if '.' in naming_series:
			prefix, hashes = naming_series.rsplit(".", 1)
		else:
			prefix, hashes = naming_series.rsplit("{", 1)
		last = frappe.db.sql("""select max(name) from `tab{0}`
						where name like %s""".format(doctype_name), prefix + "%")
		if last and last[0][0]:
			last = cint(last[0][0].replace(prefix, ""))
		else:
			last = 0

		frappe.db.sql("""update tabSeries set current = %s where name=%s""", (last, prefix))

@frappe.whitelist()
def doctypes():
	doctypes_to_be_ignored_list = ["Account", "Cost Center", "Warehouse", "Budget",
		"Party Account", "Employee", "Sales Taxes and Charges Template",
		"Purchase Taxes and Charges Template", "POS Profile", "BOM",
		"Company", "Bank Account", "Item Tax Template", "Mode Of Payment",
		"Item Default", "Customer", "Supplier", "GST Account"]
	return doctypes_to_be_ignored_list