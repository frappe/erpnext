# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.core.doctype.sms_settings.sms_settings import send_sms
import json

class HealthcareSettings(Document):
	def validate(self):
		for key in ["collect_registration_fee","manage_customer","patient_master_name",
		"require_test_result_approval","require_sample_collection", "default_medical_code_standard"]:
			frappe.db.set_default(key, self.get(key, ""))
		if(self.collect_registration_fee):
			if self.registration_fee <= 0 :
				frappe.throw("Registration fee can not be Zero")

@frappe.whitelist()
def get_sms_text(doc):
	sms_text = {}
	doc = frappe.get_doc("Lab Test",doc)
	#doc = json.loads(doc)
	context = {"doc": doc, "alert": doc, "comments": None}
	emailed = frappe.db.get_value("Healthcare Settings", None, "sms_emailed")
	sms_text['emailed'] = frappe.render_template(emailed, context)
 	printed = frappe.db.get_value("Healthcare Settings", None, "sms_printed")
	sms_text['printed'] = frappe.render_template(printed, context)
	return sms_text

def send_registration_sms(doc):
	if (frappe.db.get_value("Healthcare Settings", None, "reg_sms")=='1'):
		if doc.mobile:
			context = {"doc": doc, "alert": doc, "comments": None}
			if doc.get("_comments"):
				context["comments"] = json.loads(doc.get("_comments"))
			messages = frappe.db.get_value("Healthcare Settings", None, "reg_msg")
			messages = frappe.render_template(messages, context)
			number = [doc.mobile]
			send_sms(number,messages)
		else:
			frappe.msgprint(doc.name + " Has no mobile number to send registration SMS", alert=True)


def get_receivable_account(company):
	receivable_account = get_account(None, "receivable_account", "Healthcare Settings", company)
	if receivable_account:
		return receivable_account
	return frappe.db.get_value("Company", company, "default_receivable_account")

def get_income_account(physician, company):
	if(physician):
		income_account = get_account("Physician", None, physician, company)
		if income_account:
			return income_account
	income_account = get_account(None, "income_account", "Healthcare Settings", company)
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
