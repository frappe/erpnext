# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from datetime import date
from erpnext.setup.doctype.sms_settings.sms_settings import send_sms
class OPSettings(Document):
	def validate(self):
		for key in ["register_patient","manage_customer"]:
			frappe.db.set_default(key, self.get(key, ""))

def generate_patient_id(doc):
	if (frappe.db.get_value("OP Settings", None, "patient_id")=='1'):
		pid = make_autoname(frappe.db.get_value("OP Settings", None, "id_series"), "", doc)
		doc.patient_id = pid
		doc.save()
	send_registration_sms(doc)

def send_registration_sms(doc):
	if (frappe.db.get_value("OP Settings", None, "reg_sms")=='1'):
		context = {"doc": doc, "alert": doc, "comments": None}
		if doc.get("_comments"):
			context["comments"] = json.loads(doc.get("_comments"))
		messages = frappe.db.get_value("OP Settings", None, "reg_msg")
		messages = frappe.render_template(messages, context)
		number = [doc.mobile]
		send_sms(number,messages)
		
def get_receivable_account(patient, company):
	if(patient):
		receivable_account = get_account("Patient", None, patient, company)
		if receivable_account:
			return receivable_account
	receivable_account = get_account(None, "receivable_account", "OP Settings", company)
	if receivable_account:
		return receivable_account
	return frappe.db.get_value("Company", company, "default_receivable_account")

def get_income_account(physician, company):
	if(physician):
		income_account = get_account("Physician", None, physician, company)
		if income_account:
			return income_account
	income_account = get_account(None, "income_account", "OP Settings", company)
	if income_account:
		return income_account
	return frappe.db.get_value("Company", company, "default_income_account")

def get_account(parent_type, parent_field, parent, company):
	if(parent_type):
		return frappe.db.get_value("Party Account",
			{"parenttype": parent_type, "parent": parent, "company": company}, "account")
	if(parent_field):
		return frappe.db.get_value("Party Account",
			{"parentfield": parent_field, "parent": parent, "company": company}, "account")
