# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils import getdate
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account
from frappe import _

class LabTest(Document):
	def on_submit(self):
		frappe.db.set_value(self.doctype,self.name,"submitted_date", getdate())
		insert_lab_test_to_medical_record(self)
		frappe.db.set_value("Lab Test", self.name, "status", "Completed")

	def on_cancel(self):
		delete_lab_test_from_medical_record(self)
		frappe.db.set_value("Lab Test", self.name, "status", "Cancelled")
		self.reload()

	def on_update(self):
		if(self.sensitivity_test_items):
			sensitivity = sorted(self.sensitivity_test_items, key=lambda x: x.antibiotic_sensitivity)
			for i, item in enumerate(sensitivity):
				item.idx = i+1
			self.sensitivity_test_items = sensitivity

	def after_insert(self):
		if(self.prescription):
			frappe.db.set_value("Lab Prescription", self.prescription, "test_created", 1)
		if not self.test_name and self.template:
			self.load_test_from_template()
			self.reload()

	def load_test_from_template(self):
		lab_test = self
		create_test_from_template(lab_test)
		self.reload()

def create_test_from_template(lab_test):
	template = frappe.get_doc("Lab Test Template", lab_test.template)
	patient = frappe.get_doc("Patient", lab_test.patient)

	lab_test.test_name = template.test_name
	lab_test.result_date = getdate()
	lab_test.department = template.department
	lab_test.test_group = template.test_group

	lab_test = create_sample_collection(lab_test, template, patient, None)
	lab_test = load_result_format(lab_test, template, None, None)

@frappe.whitelist()
def update_status(status, name):
	frappe.db.sql("""update `tabLab Test` set status=%s, approved_date=%s where name = %s""", (status, getdate(), name))

@frappe.whitelist()
def update_lab_test_print_sms_email_status(print_sms_email, name):
	frappe.db.set_value("Lab Test",name,print_sms_email,1)

def create_lab_test_doc(invoice, consultation, patient, template):
	#create Test Result for template, copy vals from Invoice
	lab_test = frappe.new_doc("Lab Test")
	if(invoice):
		lab_test.invoice = invoice
	if(consultation):
		lab_test.physician = consultation.physician
	lab_test.patient = patient.name
	lab_test.patient_age = patient.get_age()
	lab_test.patient_sex = patient.sex
	lab_test.email = patient.email
	lab_test.mobile = patient.mobile
	lab_test.department = template.department
	lab_test.test_name = template.test_name
	lab_test.template = template.name
	lab_test.test_group = template.test_group
	lab_test.result_date = getdate()
	lab_test.report_preference = patient.report_preference
	return lab_test

def create_normals(template, lab_test):
	lab_test.normal_toggle = "1"
	normal = lab_test.append("normal_test_items")
	normal.test_name = template.test_name
	normal.test_uom = template.test_uom
	normal.normal_range = template.test_normal_range
	normal.require_result_value = 1
	normal.template = template.name

def create_compounds(template, lab_test, is_group):
	lab_test.normal_toggle = "1"
	for normal_test_template in template.normal_test_templates:
		normal = lab_test.append("normal_test_items")
		if is_group:
			normal.test_event = normal_test_template.test_event
		else:
			normal.test_name = normal_test_template.test_event

		normal.test_uom = normal_test_template.test_uom
		normal.normal_range = normal_test_template.normal_range
		normal.require_result_value = 1
		normal.template = template.name

def create_specials(template, lab_test):
	lab_test.special_toggle = "1"
	if(template.sensitivity):
		lab_test.sensitivity_toggle = "1"
	for special_test_template in template.special_test_template:
		special = lab_test.append("special_test_items")
		special.test_particulars = special_test_template.particulars
		special.require_result_value = 1
		special.template = template.name

def create_sample_doc(template, patient, invoice):
	if(template.sample):
		sample_exist = frappe.db.exists({
			"doctype": "Sample Collection",
			"patient": patient.name,
			"docstatus": 0,
			"sample": template.sample})
		if sample_exist :
			#Update Sample Collection by adding quantity
			sample_collection = frappe.get_doc("Sample Collection",sample_exist[0][0])
			quantity = int(sample_collection.sample_quantity)+int(template.sample_quantity)
			if(template.sample_collection_details):
				sample_collection_details = sample_collection.sample_collection_details+"\n==============\n"+"Test :"+template.test_name+"\n"+"Collection Detials:\n\t"+template.sample_collection_details
				frappe.db.set_value("Sample Collection", sample_collection.name, "sample_collection_details",sample_collection_details)
			frappe.db.set_value("Sample Collection", sample_collection.name, "sample_quantity",quantity)

		else:
			#create Sample Collection for template, copy vals from Invoice
			sample_collection = frappe.new_doc("Sample Collection")
			if(invoice):
				sample_collection.invoice = invoice
			sample_collection.patient = patient.name
			sample_collection.patient_age = patient.get_age()
			sample_collection.patient_sex = patient.sex
			sample_collection.sample = template.sample
			sample_collection.sample_uom = template.sample_uom
			sample_collection.sample_quantity = template.sample_quantity
			if(template.sample_collection_details):
				sample_collection.sample_collection_details = "Test :"+template.test_name+"\n"+"Collection Detials:\n\t"+template.sample_collection_details
			sample_collection.save(ignore_permissions=True)

		return sample_collection

@frappe.whitelist()
def create_lab_test_from_desk(patient, template, prescription, invoice=None):
	lab_test_exist = frappe.db.exists({
		"doctype": "Lab Test",
		"prescription": prescription
		})
	if lab_test_exist:
		return
	template = frappe.get_doc("Lab Test Template", template)
	#skip the loop if there is no test_template for Item
	if not (template):
		return
	patient = frappe.get_doc("Patient", patient)
	consultation_id = frappe.get_value("Lab Prescription", prescription, "parent")
	consultation = frappe.get_doc("Consultation", consultation_id)
	lab_test = create_lab_test(patient, template, prescription, consultation, invoice)
	return lab_test.name

def create_sample_collection(lab_test, template, patient, invoice):
	if(frappe.db.get_value("Healthcare Settings", None, "require_sample_collection") == "1"):
		sample_collection = create_sample_doc(template, patient, invoice)
		if(sample_collection):
			lab_test.sample = sample_collection.name
	return lab_test

def load_result_format(lab_test, template, prescription, invoice):
	if(template.test_template_type == 'Single'):
		create_normals(template, lab_test)
	elif(template.test_template_type == 'Compound'):
		create_compounds(template, lab_test, False)
	elif(template.test_template_type == 'Descriptive'):
		create_specials(template, lab_test)
	elif(template.test_template_type == 'Grouped'):
		#iterate for each template in the group and create one result for all.
		for test_group in template.test_groups:
			#template_in_group = None
			if(test_group.test_template):
				template_in_group = frappe.get_doc("Lab Test Template",
								test_group.test_template)
				if(template_in_group):
					if(template_in_group.test_template_type == 'Single'):
						create_normals(template_in_group, lab_test)
					elif(template_in_group.test_template_type == 'Compound'):
						normal_heading = lab_test.append("normal_test_items")
						normal_heading.test_name = template_in_group.test_name
						normal_heading.require_result_value = 0
						normal_heading.template = template_in_group.name
						create_compounds(template_in_group, lab_test, True)
					elif(template_in_group.test_template_type == 'Descriptive'):
						special_heading = lab_test.append("special_test_items")
						special_heading.test_name = template_in_group.test_name
						special_heading.require_result_value = 0
						special_heading.template = template_in_group.name
						create_specials(template_in_group, lab_test)
			else:
				normal = lab_test.append("normal_test_items")
				normal.test_name = test_group.group_event
				normal.test_uom = test_group.group_test_uom
				normal.normal_range = test_group.group_test_normal_range
				normal.require_result_value = 1
				normal.template = template.name
	if(template.test_template_type != 'No Result'):
		if(prescription):
			lab_test.prescription = prescription
			if(invoice):
				frappe.db.set_value("Lab Prescription", prescription, "invoice", invoice)
		lab_test.save(ignore_permissions=True) # insert the result
		return lab_test

def create_lab_test(patient, template, prescription,  consultation, invoice):
	lab_test = create_lab_test_doc(invoice, consultation, patient, template)
	lab_test = create_sample_collection(lab_test, template, patient, invoice)
	lab_test = load_result_format(lab_test, template, prescription, invoice)
	return lab_test

@frappe.whitelist()
def get_employee_by_user_id(user_id):
	emp_id = frappe.db.get_value("Employee",{"user_id":user_id})
	employee = frappe.get_doc("Employee",emp_id)
	return employee

def insert_lab_test_to_medical_record(doc):
	subject = str(doc.test_name)
	if(doc.test_comment):
		subject += ", \n"+str(doc.test_comment)
	medical_record = frappe.new_doc("Patient Medical Record")
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = "Open"
	medical_record.communication_date = doc.result_date
	medical_record.reference_doctype = "Lab Test"
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)

def delete_lab_test_from_medical_record(self):
	medical_record_id = frappe.db.sql("select name from `tabPatient Medical Record` where reference_name=%s",(self.name))

	if(medical_record_id[0][0]):
		frappe.delete_doc("Patient Medical Record", medical_record_id[0][0])

def create_item_line(test_code, sales_invoice):
	if test_code:
		item = frappe.get_doc("Item", test_code)
		if item:
			if not item.disabled:
				sales_invoice_line = sales_invoice.append("items")
				sales_invoice_line.item_code = item.item_code
				sales_invoice_line.item_name =  item.item_name
				sales_invoice_line.qty = 1.0
				sales_invoice_line.description = item.description

@frappe.whitelist()
def create_invoice(company, patient, lab_tests, prescriptions):
	test_ids = json.loads(lab_tests)
	line_ids = json.loads(prescriptions)
	if not test_ids and not line_ids:
		return
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient, "customer")
	sales_invoice.due_date = getdate()
	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(company)
	for line in line_ids:
		test_code = frappe.get_value("Lab Prescription", line, "test_code")
		create_item_line(test_code, sales_invoice)
	for test in test_ids:
		template = frappe.get_value("Lab Test", test, "template")
		test_code = frappe.get_value("Lab Test Template", template, "item")
		create_item_line(test_code, sales_invoice)
	sales_invoice.set_missing_values()
	sales_invoice.save()
	#set invoice in lab test
	for test in test_ids:
		frappe.db.set_value("Lab Test", test, "invoice", sales_invoice.name)
		prescription = frappe.db.get_value("Lab Test", test, "prescription")
		if prescription:
			frappe.db.set_value("Lab Prescription", prescription, "invoice", sales_invoice.name)
	#set invoice in prescription
	for line in line_ids:
		frappe.db.set_value("Lab Prescription", line, "invoice", sales_invoice.name)
	return sales_invoice.name

@frappe.whitelist()
def get_lab_test_prescribed(patient):
	return frappe.db.sql(_("""select cp.name, cp.test_code, cp.parent, cp.invoice, ct.physician, ct.consultation_date from tabConsultation ct,
	`tabLab Prescription` cp where ct.patient='{0}' and cp.parent=ct.name and cp.test_created=0""").format(patient))
