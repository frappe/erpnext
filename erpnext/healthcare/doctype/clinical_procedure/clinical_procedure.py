# -*- coding: utf-8 -*-
# Copyright (c) 2017, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_account
from erpnext.healthcare.doctype.lab_test.lab_test import create_sample_doc

class ClinicalProcedure(Document):
	def after_insert(self):
		if self.maintain_stock:
			doc = set_stock_items(self, self.procedure_template, "Procedure Template")
			doc.save()
		if self.appointment:
			frappe.db.set_value("Procedure Appointment", self.appointment, "status", "Closed")
		if self.is_staged:
			doc = set_stage_detail(self)
			doc.save()
		template = frappe.get_doc("Procedure Template", self.procedure_template)
		if template.sample:
			patient = frappe.get_doc("Patient", self.patient)
			sample_collection = create_sample_doc(template, patient, None)
			frappe.db.set_value("Clinical Procedure", self.name, "sample", sample_collection.name)
		self.reload()
	def complete(self):
		if self.maintain_stock:
			create_stock_entry(self)
		frappe.db.set_value("Clinical Procedure", self.name, "complete_procedure", 1)

@frappe.whitelist()
def set_stock_items(doc, stock_detail_parent, parenttype):
	item_dict = get_item_dict("Procedure Stock Detail", stock_detail_parent, parenttype)

	for d in item_dict:
		se_child = doc.append('items')
		se_child.barcode = d["barcode"]
		se_child.item_code = d["item_code"]
		se_child.item_name = d["item_name"]
		se_child.uom = d["uom"]
		se_child.stock_uom = d["stock_uom"]
		se_child.qty = flt(d["qty"])
		# in stock uom
		se_child.transfer_qty = flt(d["transfer_qty"])
		se_child.conversion_factor = flt(d["conversion_factor"])

	return doc

def set_stage_detail(doc):
	stages = get_item_dict("Template Stage Detail", doc.procedure_template, "Procedure Template")

	for d in stages:
		child = doc.append('stages')
		child.stage = d["stage"]

	return doc

def get_item_dict(table, parent, parenttype):
	query = """select * from `tab{table}` where parent = '{parent}' and parenttype = '{parenttype}' """

	return frappe.db.sql(query.format(table=table, parent=parent, parenttype=parenttype), as_dict=True)

def create_stock_entry(doc):
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry = set_stock_items(stock_entry, doc.name, "Clinical Procedure")
	stock_entry.purpose = "Material Issue"
	warehouse = frappe.db.get_value("Service Unit", doc.service_unit, "warehouse")
	expense_account = get_account(None, "expense_account", "Healthcare Settings", doc.company)

	for item_line in stock_entry.items:
		cost_center = frappe.db.get_value("Item", item_line.item_code, "buying_cost_center")
		item_line.s_warehouse = warehouse
		item_line.cost_center = cost_center
		#if not expense_account:
		#	expense_account = frappe.db.get_value("Item", item_line.item_code, "expense_account")
		item_line.expense_account = expense_account

	stock_entry.insert(ignore_permissions = True)
	stock_entry.submit()
