# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe import scrub
from frappe.utils import cstr

class AccountingDimension(Document):

	def before_insert(self):
		self.set_fieldname_and_label()
		self.make_accounting_dimension_in_accounting_doctypes()

	def on_trash(self):
		self.delete_accounting_dimension()

	def set_fieldname_and_label(self):
		if not self.label:
			self.label = cstr(self.document_type)

		if not self.fieldname:
			self.fieldname = scrub(self.label)

	def make_accounting_dimension_in_accounting_doctypes(self):

		doclist = ["GL Entry", "Sales Invoice", "Purchase Invoice", "Payment Entry", "BOM", "Sales Order", "Purchase Order", "Asset",
			"Stock Entry", "Budget", "Payroll Entry", "Delivery Note", "Sales Invoice Item", "Purchase Invoice Item", "Sales Order Item",
			"Purchase Order Item", "Journal Entry Account", "Material Request Item", "Delivery Note Item", "Purchase Receipt Item",
			"Purchase Order Item"]

		if self.is_mandatory:
			df.update({
				"reqd": 1
			})

		for doctype in doclist:

			df = {
				"fieldname": self.fieldname,
				"label": self.label,
				"fieldtype": "Link",
				"options": self.document_type,
				"insert_after": "cost_center"
			}

			if doctype == "Budget":
				df.update({
					"depends_on": "eval:doc.budget_against == '{0}'".format(self.document_type)
				})

				create_custom_field(doctype, df)

				property_setter = frappe.db.exists("Property Setter", "Budget-budget_against-options")

				if property_setter:
					property_setter_doc = frappe.get_doc("Property Setter", "Budget-budget_against-options")
					property_setter_doc.doc_type = 'Budget'
					property_setter_doc.doctype_or_field = "DocField"
					property_setter_doc.fiel_dname = "budget_against"
					property_setter_doc.property = "options"
					property_setter_doc.property_type = "Text"
					property_setter_doc.value = property_setter_doc.value + "\n" + self.document_type
					property_setter_doc.save()

					frappe.clear_cache(doctype='Budget')
				else:
					frappe.get_doc({
						"doctype": "Property Setter",
						"doctype_or_field": "DocField",
						"doc_type": "Budget",
						"field_name": "budget_against",
						"property": "options",
						"property_type": "Text",
						"value": "\nCost Center\nProject\n" + self.document_type
					}).insert(ignore_permissions=True)
				frappe.clear_cache(doctype=doctype)
			else:
				create_custom_field(doctype, df)
				frappe.clear_cache(doctype=doctype)

	def delete_accounting_dimension(self):
		doclist = ["GL Entry", "Sales Invoice", "Purchase Invoice", "Payment Entry", "BOM", "Sales Order", "Purchase Order", "Asset",
			"Stock Entry", "Budget", "Payroll Entry", "Delivery Note", "Sales Invoice Item", "Purchase Invoice Item", "Sales Order Item",
			"Purchase Order Item", "Journal Entry Account", "Material Request Item", "Delivery Note Item", "Purchase Receipt Item",
			"Purchase Order Item"]

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

		budget_against_property = frappe.get_doc("Property Setter", "Budget-budget_against-options")
		value_list = budget_against_property.value.split('\n')[3:]
		value_list.remove(self.document_type)

		budget_against_property.value = "\nCost Center\nProject\n" + "\n".join(value_list)
		budget_against_property.save()

		for doc in doclist:
			frappe.clear_cache(doctype=doc)

def get_accounting_dimensions():
	accounting_dimensions = frappe.get_all("Accounting Dimension", fields=["fieldname"])

	return [d.fieldname for d in accounting_dimensions]
