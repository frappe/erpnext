# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, cstr, getdate, get_time
import time
from erpnext.medical.doctype.op_settings.op_settings import generate_patient_id
from erpnext.accounts.party import validate_party_accounts
from erpnext.medical.doctype.patient_medical_record.patient_medical_record import delete_attachment, insert_attachment
from erpnext.medical.doctype.op_settings.op_settings import get_receivable_account,get_income_account
class Patient(Document):
	def validate(self):
		validate_party_accounts(self)
	def after_insert(self):
		generate_patient_id(self)
		if(frappe.db.get_value("OP Settings", None, "manage_customer") == '1' and not self.customer):
			create_customer(self)
		if(frappe.db.get_value("OP Settings", None, "register_patient") == '1'):
			frappe.db.set_value("Patient", self.name, "status", "Open")
			self.reload()
	def autoname(self):
		self.name = self.get_patient_name()

	def on_trash(self):
		frappe.throw("""Not permitted. Please disable Patient""")

	def on_update(self):
		attachments = get_attachments(self)
		if attachments:
			delete_attachment("File", self.name)
			for i in range(0,len(attachments)):
				attachment = frappe.get_doc("File", attachments[i]['name'])
				insert_attachment(attachment,attachment.attached_to_name)

	def get_patient_name(self):
		name = " ".join(filter(None,
			[cstr(self.get(f)).strip() for f in ["patient_name","middle_name","last_name"]]))
		if frappe.db.get_value("Patient", name):
			count = frappe.db.sql("""select ifnull(MAX(CAST(SUBSTRING_INDEX(name, ' ', -1) AS UNSIGNED)), 0) from tabPatient
				 where name like %s""", "%{0} - %".format(name), as_list=1)[0][0]
			count = cint(count) + 1
			return "{0} - {1}".format(name, cstr(count))

		return name

def get_attachments(doc):
	return frappe.get_all("File", fields=["name"],
		filters = {"attached_to_name": doc.name, "attached_to_doctype": doc.doctype})

def create_customer(doc):
	customer_group = frappe.get_value("Selling Settings", None, "customer_group")
	territory = frappe.get_value("Selling Settings", None, "territory")
	if not (customer_group and territory):
		frappe.throw("Please set default customer group and territory in Selling Settings")
	customer = frappe.get_doc({"doctype": "Customer",
	"customer_name": doc.name,
	"territory": doc.territory,
	"customer_group": customer_group,
	"territory" : territory,
	"customer_type": "Individual"
	}).insert(ignore_permissions=True)
	frappe.db.set_value("Patient", doc.name, "customer", customer.name)
	frappe.msgprint(_("Customer {0} is created.").format(customer.name))
	doc.reload()

@frappe.whitelist()
def register_patient(patient, company=None):
	frappe.db.set_value("Patient", patient, "status", "Active")
	if(frappe.get_value("OP Settings", None, "registration_fee")>0):
		sales_invoice = make_invoice(patient, company)
		sales_invoice.save(ignore_permissions=True)
		return {'invoice': sales_invoice.name}

def make_invoice(patient, company):
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient, "customer")
	sales_invoice.due_date = getdate()
	sales_invoice.company = company
	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(patient, company)

	item_line = sales_invoice.append("items")
	item_line.item_name = "Registeration Fee"
	item_line.description = "Registeration Fee"
	item_line.qty = 1
	item_line.uom = "Nos"
	item_line.conversion_factor = 1
	item_line.income_account = get_income_account(None, company)
	item_line.rate = frappe.get_value("OP Settings", None, "registration_fee")
	item_line.amount = item_line.rate
	sales_invoice.set_missing_values()
	return sales_invoice

@frappe.whitelist()
def get_patient_detail(patient, company=None):
	patient_dict = frappe.db.sql(_("""select * from tabPatient where name='{0}'""").format(patient), as_dict=1)
	if not patient_dict:
		frappe.throw("Patient not found")
	vital_sign = frappe.db.sql(_("""select * from `tabVital Signs` where patient='{0}' order by signs_date desc limit 1""").format(patient), as_dict=1)

	details = patient_dict[0]
	if vital_sign:
		details.update(vital_sign[0])
	return details
