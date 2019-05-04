# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe import scrub

class Dimension(Document):

	def before_insert(self):
		self.set_fieldname()
		self.make_dimension_in_accounting_doctypes()

	def on_trash(self):
		self.delete_dimension()

	def set_fieldname(self):
		if not self.fieldname:
			self.fieldname = scrub(self.label)

	def make_dimension_in_accounting_doctypes(self):
		last_created_dimension = get_last_created_dimension()

		doclist = ["GL Entry", "Sales Invoice", "Purchase Invoice", "Payment Entry", "BOM", "Sales Order", "Purchase Order",
			"Stock Entry", "Budget", "Payroll Entry", "Delivery Note"]

		df = {
			"fieldname": self.fieldname,
			"label": self.label,
			"fieldtype": "Data",
			"insert_after": last_created_dimension if last_created_dimension else "project"
		}

		for doctype in doclist:
			create_custom_field(doctype, df)

	def delete_dimension(self):
		doclist = ["GL Entry", "Sales Invoice", "Purchase Invoice", "Payment Entry", "BOM", "Sales Order", "Purchase Order",
			"Stock Entry", "Budget", "Payroll Entry", "Delivery Note"]

		frappe.db.sql("""
			DELETE FROM `tabCustom Field`
			WHERE  fieldname = %s
			AND dt IN (%s)""" %
			('%s', ', '.join(['%s']* len(doclist))), tuple([self.fieldname] + doclist))

		frappe.db.sql("""
			DELETE FROM `tabProperty Setter`
			WHERE  field_name = %s
			AND doc_type IN (%s)""" %
			('%s', ', '.join(['%s']* len(doclist))), tuple([self.fieldname] + doclist))

		for doc in doclist:
			frappe.clear_cache(doctype=doc)


def get_last_created_dimension():
	last_created_dimension = frappe.db.sql("select fieldname, max(creation) from `tabDimension`", as_dict=1)

	if last_created_dimension[0]:
		return last_created_dimension[0].fieldname
