# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, cstr

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
			frappe.db.set_value("Lab Prescription", self.prescription, "lab_test_created", 1)
			if frappe.db.get_value("Lab Prescription", self.prescription, 'invoiced') == 1:
				self.invoiced = True
		if not self.lab_test_name and self.template:
			self.load_test_from_template()
			self.reload()

	def load_test_from_template(self):
		lab_test = self
		create_test_from_template(lab_test)
		self.reload()

def create_test_from_template(lab_test):
	template = frappe.get_doc("Lab Test Template", lab_test.template)
	patient = frappe.get_doc("Patient", lab_test.patient)

	lab_test.lab_test_name = template.lab_test_name
	lab_test.result_date = getdate()
	lab_test.department = template.department
	lab_test.lab_test_group = template.lab_test_group

	lab_test = create_sample_collection(lab_test, template, patient, None)
	lab_test = load_result_format(lab_test, template, None, None)

@frappe.whitelist()
def update_status(status, name):
	frappe.db.sql("""update `tabLab Test` set status=%s, approved_date=%s where name = %s""", (status, getdate(), name))

@frappe.whitelist()
def update_lab_test_print_sms_email_status(print_sms_email, name):
	frappe.db.set_value("Lab Test",name,print_sms_email,1)

@frappe.whitelist()
def create_multiple(doctype, docname):
	lab_test_created = False
	if doctype == "Sales Invoice":
		lab_test_created = create_lab_test_from_invoice(docname)
	elif doctype == "Patient Encounter":
		lab_test_created = create_lab_test_from_encounter(docname)

	if lab_test_created:
		frappe.msgprint(_("Lab Test(s) "+lab_test_created+" created."))
	else:
		frappe.msgprint(_("No Lab Test created"))

def create_lab_test_from_encounter(encounter_id):
	lab_test_created = False
	encounter = frappe.get_doc("Patient Encounter", encounter_id)

	lab_test_ids = frappe.db.sql("""select lp.name, lp.lab_test_code, lp.invoiced
	from `tabPatient Encounter` et, `tabLab Prescription` lp
	where et.patient=%s and lp.parent=%s and
	lp.parent=et.name and lp.lab_test_created=0 and et.docstatus=1""", (encounter.patient, encounter_id))

	if lab_test_ids:
		patient = frappe.get_doc("Patient", encounter.patient)
		for lab_test_id in lab_test_ids:
			template = get_lab_test_template(lab_test_id[1])
			if template:
				lab_test = create_lab_test_doc(lab_test_id[2], encounter.practitioner, patient, template)
				lab_test.save(ignore_permissions = True)
				frappe.db.set_value("Lab Prescription", lab_test_id[0], "lab_test_created", 1)
				if not lab_test_created:
					lab_test_created = lab_test.name
				else:
					lab_test_created += ", "+lab_test.name
	return lab_test_created


def create_lab_test_from_invoice(invoice_name):
	lab_tests_created = False
	invoice = frappe.get_doc("Sales Invoice", invoice_name)
	if invoice.patient:
		patient = frappe.get_doc("Patient", invoice.patient)
		for item in invoice.items:
			lab_test_created = 0
			if item.reference_dt == "Lab Prescription":
				lab_test_created = frappe.db.get_value("Lab Prescription", item.reference_dn, "lab_test_created")
			elif item.reference_dt == "Lab Test":
				lab_test_created = 1
			if lab_test_created != 1:
				template = get_lab_test_template(item.item_code)
				if template:
					lab_test = create_lab_test_doc(True, invoice.ref_practitioner, patient, template)
					if item.reference_dt == "Lab Prescription":
						lab_test.prescription = item.reference_dn
					lab_test.save(ignore_permissions = True)
					if item.reference_dt != "Lab Prescription":
						frappe.db.set_value("Sales Invoice Item", item.name, "reference_dt", "Lab Test")
						frappe.db.set_value("Sales Invoice Item", item.name, "reference_dn", lab_test.name)
					if not lab_tests_created:
						lab_tests_created = lab_test.name
					else:
						lab_tests_created += ", "+lab_test.name
	return lab_tests_created

def get_lab_test_template(item):
	template_id = check_template_exists(item)
	if template_id:
		return frappe.get_doc("Lab Test Template", template_id)
	return False

def check_template_exists(item):
	template_exists = frappe.db.exists(
		"Lab Test Template",
		{
			'item': item
		}
	)
	if template_exists:
		return template_exists
	return False

def create_lab_test_doc(invoiced, practitioner, patient, template):
	lab_test = frappe.new_doc("Lab Test")
	lab_test.invoiced = invoiced
	lab_test.practitioner = practitioner
	lab_test.patient = patient.name
	lab_test.patient_age = patient.get_age()
	lab_test.patient_sex = patient.sex
	lab_test.email = patient.email
	lab_test.mobile = patient.mobile
	lab_test.department = template.department
	lab_test.template = template.name
	lab_test.lab_test_group = template.lab_test_group
	lab_test.result_date = getdate()
	lab_test.report_preference = patient.report_preference
	return lab_test

def create_normals(template, lab_test):
	lab_test.normal_toggle = "1"
	normal = lab_test.append("normal_test_items")
	normal.lab_test_name = template.lab_test_name
	normal.lab_test_uom = template.lab_test_uom
	normal.normal_range = template.lab_test_normal_range
	normal.require_result_value = 1
	normal.template = template.name

def create_compounds(template, lab_test, is_group):
	lab_test.normal_toggle = "1"
	for normal_test_template in template.normal_test_templates:
		normal = lab_test.append("normal_test_items")
		if is_group:
			normal.lab_test_event = normal_test_template.lab_test_event
		else:
			normal.lab_test_name = normal_test_template.lab_test_event

		normal.lab_test_uom = normal_test_template.lab_test_uom
		normal.normal_range = normal_test_template.normal_range
		normal.require_result_value = 1
		normal.template = template.name

def create_specials(template, lab_test):
	lab_test.special_toggle = "1"
	if(template.sensitivity):
		lab_test.sensitivity_toggle = "1"
	for special_test_template in template.special_test_template:
		special = lab_test.append("special_test_items")
		special.lab_test_particulars = special_test_template.particulars
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
				sample_collection_details = sample_collection.sample_collection_details+"\n==============\n"+"Test :"+template.lab_test_name+"\n"+"Collection Detials:\n\t"+template.sample_collection_details
				frappe.db.set_value("Sample Collection", sample_collection.name, "sample_collection_details",sample_collection_details)
			frappe.db.set_value("Sample Collection", sample_collection.name, "sample_quantity",quantity)

		else:
			#create Sample Collection for template, copy vals from Invoice
			sample_collection = frappe.new_doc("Sample Collection")
			if(invoice):
				sample_collection.invoiced = True
			sample_collection.patient = patient.name
			sample_collection.patient_age = patient.get_age()
			sample_collection.patient_sex = patient.sex
			sample_collection.sample = template.sample
			sample_collection.sample_uom = template.sample_uom
			sample_collection.sample_quantity = template.sample_quantity
			if(template.sample_collection_details):
				sample_collection.sample_collection_details = "Test :"+template.lab_test_name+"\n"+"Collection Detials:\n\t"+template.sample_collection_details
			sample_collection.save(ignore_permissions=True)

		return sample_collection

def create_sample_collection(lab_test, template, patient, invoice):
	if(frappe.db.get_value("Healthcare Settings", None, "require_sample_collection") == "1"):
		sample_collection = create_sample_doc(template, patient, invoice)
		if(sample_collection):
			lab_test.sample = sample_collection.name
	return lab_test

def load_result_format(lab_test, template, prescription, invoice):
	if(template.lab_test_template_type == 'Single'):
		create_normals(template, lab_test)
	elif(template.lab_test_template_type == 'Compound'):
		create_compounds(template, lab_test, False)
	elif(template.lab_test_template_type == 'Descriptive'):
		create_specials(template, lab_test)
	elif(template.lab_test_template_type == 'Grouped'):
		#iterate for each template in the group and create one result for all.
		for lab_test_group in template.lab_test_groups:
			#template_in_group = None
			if(lab_test_group.lab_test_template):
				template_in_group = frappe.get_doc("Lab Test Template",
								lab_test_group.lab_test_template)
				if(template_in_group):
					if(template_in_group.lab_test_template_type == 'Single'):
						create_normals(template_in_group, lab_test)
					elif(template_in_group.lab_test_template_type == 'Compound'):
						normal_heading = lab_test.append("normal_test_items")
						normal_heading.lab_test_name = template_in_group.lab_test_name
						normal_heading.require_result_value = 0
						normal_heading.template = template_in_group.name
						create_compounds(template_in_group, lab_test, True)
					elif(template_in_group.lab_test_template_type == 'Descriptive'):
						special_heading = lab_test.append("special_test_items")
						special_heading.lab_test_name = template_in_group.lab_test_name
						special_heading.require_result_value = 0
						special_heading.template = template_in_group.name
						create_specials(template_in_group, lab_test)
			else:
				normal = lab_test.append("normal_test_items")
				normal.lab_test_name = lab_test_group.group_event
				normal.lab_test_uom = lab_test_group.group_test_uom
				normal.normal_range = lab_test_group.group_test_normal_range
				normal.require_result_value = 1
				normal.template = template.name
	if(template.lab_test_template_type != 'No Result'):
		if(prescription):
			lab_test.prescription = prescription
			if(invoice):
				frappe.db.set_value("Lab Prescription", prescription, "invoiced", True)
		lab_test.save(ignore_permissions=True) # insert the result
		return lab_test

@frappe.whitelist()
def get_employee_by_user_id(user_id):
	emp_id = frappe.db.get_value("Employee",{"user_id":user_id})
	employee = frappe.get_doc("Employee",emp_id)
	return employee

def insert_lab_test_to_medical_record(doc):
	table_row = False
	subject = cstr(doc.lab_test_name)
	if doc.practitioner:
		subject += " "+ doc.practitioner
	if doc.normal_test_items:
		item = doc.normal_test_items[0]
		comment = ""
		if item.lab_test_comment:
			comment = str(item.lab_test_comment)
		event = ""
		if item.lab_test_event:
			event = item.lab_test_event
		table_row = item.lab_test_name +" "+ event +" "+ item.result_value
		if item.normal_range:
			table_row += " normal_range("+item.normal_range+")"
		table_row += " "+comment

	elif doc.special_test_items:
		item = doc.special_test_items[0]
		table_row = item.lab_test_particulars +" "+ item.result_value

	elif doc.sensitivity_test_items:
		item = doc.sensitivity_test_items[0]
		table_row = item.antibiotic +" "+ item.antibiotic_sensitivity

	if table_row:
		subject += "<br/>"+table_row
	if doc.lab_test_comment:
		subject += "<br/>"+ cstr(doc.lab_test_comment)

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

	if medical_record_id and medical_record_id[0][0]:
		frappe.delete_doc("Patient Medical Record", medical_record_id[0][0])

@frappe.whitelist()
def get_lab_test_prescribed(patient):
	return frappe.db.sql("""select cp.name, cp.lab_test_code, cp.parent, cp.invoiced, ct.practitioner, ct.encounter_date from `tabPatient Encounter` ct,
	`tabLab Prescription` cp where ct.patient=%s and cp.parent=ct.name and cp.lab_test_created=0""", (patient))
