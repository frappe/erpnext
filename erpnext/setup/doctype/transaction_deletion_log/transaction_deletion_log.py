# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import cint
import frappe
from frappe.model.document import Document
from frappe import _

class TransactionDeletionLog(Document):
	def validate(self):
		doctypes_to_be_ignored_list = get_doctypes_to_be_ignored()
		for doctype in self.doctypes_to_be_ignored:
			if doctype.doctype_name not in doctypes_to_be_ignored_list:
				print("*" * 100)
				print(doctype.doctype_name)
				frappe.throw(_("DocTypes should not be added manually to the 'DocTypes That Won't Be Affected' table."))

	def before_submit(self):
		singles = frappe.get_all('DocType', filters = {'issingle': 1}, pluck = "name")
		tables = frappe.get_all('DocType', filters = {'istable': 1}, pluck = "name")
		doctypes_to_be_ignored_list = singles + get_doctypes_to_be_ignored()
		docfields = frappe.get_all('Docfield', 
			filters = {
				'fieldtype': 'Link', 
				'options': 'Company',
				'parent': ['not in', doctypes_to_be_ignored_list]},
			fields=["parent", "fieldname"])
	
		for docfield in docfields:
			if docfield['parent'] != self.doctype:
				no_of_docs = frappe.db.count(docfield['parent'], {
							docfield['fieldname'] : self.company
						})
				if no_of_docs > 0:
					# populate DocTypes table
					if docfield['parent'] not in tables:
						self.append('doctypes', {
							"doctype_name" : docfield['parent'],
							"no_of_docs" : no_of_docs
						})

					# delete the docs linked with the specified company
					frappe.db.delete(docfield['parent'], {
						docfield['fieldname'] : self.company
					})

					naming_series = frappe.db.get_value('DocType', docfield['parent'], 'autoname')
					if naming_series:
						if '#' in naming_series:
							self.update_naming_series(naming_series, docfield['parent'])			

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
def get_doctypes_to_be_ignored():
	doctypes_to_be_ignored_list = ["Account", "Cost Center", "Warehouse", "Budget",
		"Party Account", "Employee", "Sales Taxes and Charges Template",
		"Purchase Taxes and Charges Template", "POS Profile", "BOM",
		"Company", "Bank Account", "Item Tax Template", "Mode of Payment",
		"Item Default", "Customer", "Supplier", "GST Account"]
	return doctypes_to_be_ignored_list