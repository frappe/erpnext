# -*- coding: utf-8 -*-
# Copyright (c) 2017, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate, nowtime, cstr
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_account
from erpnext.healthcare.doctype.lab_test.lab_test import create_sample_doc
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.stock.get_item_details import get_item_details

class ClinicalProcedure(Document):
	def validate(self):
		if self.consume_stock and not self.status == 'Draft':
			if not self.warehouse:
				frappe.throw(_("Set warehouse for Procedure {0} ").format(self.name))
			self.set_actual_qty()

		if self.items:
			self.invoice_separately_as_consumables = False
			for item in self.items:
				if item.invoice_separately_as_consumables == 1:
					self.invoice_separately_as_consumables = True

	def before_insert(self):
		if self.consume_stock:
			set_stock_items(self, self.procedure_template, "Clinical Procedure Template")
			self.set_actual_qty();

	def after_insert(self):
		if self.prescription:
			frappe.db.set_value("Procedure Prescription", self.prescription, "procedure_created", 1)
		if self.appointment:
			frappe.db.set_value("Patient Appointment", self.appointment, "status", "Closed")
		template = frappe.get_doc("Clinical Procedure Template", self.procedure_template)
		if template.sample:
			patient = frappe.get_doc("Patient", self.patient)
			sample_collection = create_sample_doc(template, patient, None)
			frappe.db.set_value("Clinical Procedure", self.name, "sample", sample_collection.name)
		self.reload()

	def complete(self):
		if self.consume_stock:
			create_stock_entry(self)
		frappe.db.set_value("Clinical Procedure", self.name, "status", 'Completed')

		if self.items:
			consumable_total_amount = 0
			consumption_details = False
			for item in self.items:
				if item.invoice_separately_as_consumables:
					price_list, price_list_currency = frappe.db.get_values("Price List", {"selling": 1}, ['name', 'currency'])[0]
					args = {
						'doctype': "Sales Invoice",
						'item_code': item.item_code,
						'company': self.company,
						'warehouse': self.warehouse,
						'customer': frappe.db.get_value("Patient", self.patient, "customer"),
						'selling_price_list': price_list,
						'price_list_currency': price_list_currency,
						'plc_conversion_rate': 1.0,
						'conversion_rate': 1.0
					}
					item_details = get_item_details(args)
					item_price = item_details.price_list_rate * item.transfer_qty
					item_consumption_details = item_details.item_name+"\t"+str(item.qty)+" "+item.uom+"\t"+str(item_price)
					consumable_total_amount += item_price
					if not consumption_details:
						consumption_details = "Clinical Procedure ("+self.name+"):\n\t"+item_consumption_details
					else:
						consumption_details += "\n\t"+item_consumption_details
			if consumable_total_amount > 0:
				frappe.db.set_value("Clinical Procedure", self.name, "consumable_total_amount", consumable_total_amount)
				frappe.db.set_value("Clinical Procedure", self.name, "consumption_details", consumption_details)


	def start(self):
		allow_start = self.set_actual_qty()
		if allow_start:
			self.status = 'In Progress'
			insert_clinical_procedure_to_medical_record(self)
		else:
			self.status = 'Draft'
		self.save()

	def set_actual_qty(self):
		allow_negative_stock = cint(frappe.db.get_value("Stock Settings", None, "allow_negative_stock"))

		allow_start = True
		for d in self.get('items'):
			d.actual_qty = get_stock_qty(d.item_code, self.warehouse)
			# validate qty
			if not allow_negative_stock and d.actual_qty < d.qty:
				allow_start = False

		return allow_start

	def make_material_transfer(self):
		stock_entry = frappe.new_doc("Stock Entry")

		stock_entry.purpose = "Material Transfer"
		stock_entry.to_warehouse = self.warehouse
		expense_account = get_account(None, "expense_account", "Healthcare Settings", self.company)
		for item in self.items:
			if item.qty > item.actual_qty:
				se_child = stock_entry.append('items')
				se_child.item_code = item.item_code
				se_child.item_name = item.item_name
				se_child.uom = item.uom
				se_child.stock_uom = item.stock_uom
				se_child.qty = flt(item.qty-item.actual_qty)
				se_child.t_warehouse = self.warehouse
				# in stock uom
				se_child.transfer_qty = flt(item.transfer_qty)
				se_child.conversion_factor = flt(item.conversion_factor)
				cost_center = frappe.get_cached_value('Company',  self.company,  'cost_center')
				se_child.cost_center = cost_center
				se_child.expense_account = expense_account
		return stock_entry.as_dict()

@frappe.whitelist()
def get_stock_qty(item_code, warehouse):
	return get_previous_sle({
		"item_code": item_code,
		"warehouse": warehouse,
		"posting_date": nowdate(),
		"posting_time": nowtime()
	}).get("qty_after_transaction") or 0

@frappe.whitelist()
def set_stock_items(doc, stock_detail_parent, parenttype):
	item_dict = get_item_dict("Clinical Procedure Item", stock_detail_parent, parenttype)

	for d in item_dict:
		se_child = doc.append('items')
		se_child.item_code = d["item_code"]
		se_child.item_name = d["item_name"]
		se_child.uom = d["uom"]
		se_child.stock_uom = d["stock_uom"]
		se_child.qty = flt(d["qty"])
		# in stock uom
		se_child.transfer_qty = flt(d["transfer_qty"])
		se_child.conversion_factor = flt(d["conversion_factor"])
		if d["batch_no"]:
			se_child.batch_no = d["batch_no"]
		if parenttype == "Clinical Procedure Template":
			se_child.invoice_separately_as_consumables = d["invoice_separately_as_consumables"]
	return doc

def get_item_dict(table, parent, parenttype):
	query = """select * from `tab{table}` where parent = '{parent}' and parenttype = '{parenttype}' """

	return frappe.db.sql(query.format(table=table, parent=parent, parenttype=parenttype), as_dict=True)

def create_stock_entry(doc):
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry = set_stock_items(stock_entry, doc.name, "Clinical Procedure")
	stock_entry.purpose = "Material Issue"
	stock_entry.from_warehouse = doc.warehouse
	stock_entry.company = doc.company
	expense_account = get_account(None, "expense_account", "Healthcare Settings", doc.company)

	for item_line in stock_entry.items:
		cost_center = frappe.get_cached_value('Company',  doc.company,  'cost_center')
		#item_line.s_warehouse = warehouse #deaful source warehouse set, stock entry to copy to lines
		item_line.cost_center = cost_center
		#if not expense_account:
		#	expense_account = frappe.db.get_value("Item", item_line.item_code, "expense_account")
		item_line.expense_account = expense_account

	stock_entry.insert(ignore_permissions = True)
	stock_entry.submit()

@frappe.whitelist()
def create_procedure(appointment):
	appointment = frappe.get_doc("Patient Appointment",appointment)
	procedure = frappe.new_doc("Clinical Procedure")
	procedure.appointment = appointment.name
	procedure.patient = appointment.patient
	procedure.patient_age = appointment.patient_age
	procedure.patient_sex = appointment.patient_sex
	procedure.procedure_template = appointment.procedure_template
	procedure.prescription = appointment.procedure_prescription
	procedure.practitioner = appointment.practitioner
	procedure.invoiced = appointment.invoiced
	procedure.medical_department = appointment.department
	procedure.start_date = appointment.appointment_date
	procedure.start_time = appointment.appointment_time
	procedure.notes = appointment.notes
	procedure.service_unit = appointment.service_unit
	consume_stock = frappe.db.get_value("Clinical Procedure Template", appointment.procedure_template, "consume_stock")
	if consume_stock == 1:
		procedure.consume_stock = True
		warehouse = False
		if appointment.service_unit:
			warehouse = frappe.db.get_value("Healthcare Service Unit", appointment.service_unit, "warehouse")
		if not warehouse:
			warehouse = frappe.db.get_value("Stock Settings", None, "default_warehouse")
		if warehouse:
			procedure.warehouse = warehouse
	return procedure.as_dict()

def insert_clinical_procedure_to_medical_record(doc):
	subject = cstr(doc.procedure_template)
	if doc.practitioner:
		subject += " "+doc.practitioner
	if subject and doc.notes:
		subject += "<br/>"+doc.notes

	medical_record = frappe.new_doc("Patient Medical Record")
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = "Open"
	medical_record.communication_date = doc.start_date
	medical_record.reference_doctype = "Clinical Procedure"
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)
