# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import datetime
import time
from frappe.utils import getdate, get_time
from erpnext.medical.doctype.op_settings.op_settings import get_receivable_account

class PatientAdmission(Document):
	def before_insert(self):
		admission = frappe.db.sql("select name,status from `tabPatient Admission` where patient=%s and status != %s and status !=%s",(self.patient,"Discharged", "Cancelled"))
		if(admission):
			frappe.throw("The patient is already admitted or scheduled to admit")

@frappe.whitelist()
def admit_and_allocate_patient(patient, admission, date_in, time_in, bed, facility_type, facility, expected_discharge):
	allocate_facility(patient,admission,date_in,time_in,bed,facility_type, facility, expected_discharge,"Occupied",True)
	update_patient(patient, admission, True)
	update_bed(bed, patient, True)
	update_facility(facility, patient, True)
	frappe.db.set_value("Patient Admission",admission,"status","Admitted")
	frappe.db.set_value("Patient Admission",admission,"admit_date",date_in)

@frappe.whitelist()
def facility_transfer_allocation(patient,admission,bed_number,facility_type, facility_name, expected_discharge, old_facility_name):
	allocate_facility(patient, admission, datetime.date.today(), datetime.datetime.now(), bed_number, facility_type, facility_name, expected_discharge, "Occupied", True)
	update_bed(bed_number, patient, False)
	#New facility update
	update_facility(facility_name, patient, True)
	#Old facility update
	update_facility(old_facility_name, patient, False)

@frappe.whitelist()
def discharge_patient(patient,admission):
	update_patient(patient, admission, False)
	disallocate_facility_bed(admission)
	patient_admission = frappe.get_doc("Patient Admission",admission)
	update_facility(patient_admission.current_facility, patient, False)
	update_bed(None, patient, False)
	frappe.db.set_value("Patient Admission",admission,"status","Discharged")

@frappe.whitelist()
def queue_discharge_patient(patient,admission):
	frappe.db.set_value("Patient Admission",admission,"status","Queued")
	frappe.db.set_value("Patient Admission",admission,"discharge_date",datetime.date.today())

@frappe.whitelist()
def cancel_scheduled_admission(admission):
	frappe.db.set_value("Patient Admission",admission,"status","Cancelled")

@frappe.whitelist()
def allocate_facility(patient,admission,date_in,time_in,bed,facility_type, facility, expected_discharge,status,occupied):
	patient_admission = frappe.get_doc("Patient Admission",admission)
	#Validate the facility already occupied,leaved the previous patient when schedule and admit the patient to the facility
	if(patient_admission.facility_alloc):
		for allocations in patient_admission.facility_alloc:
			allocations.status = "Left" #All other allocated facility marked as Left in Admission
	if(patient_admission.facility_alloc and patient_admission.status == "Scheduled"):
		allocation = patient_admission.facility_alloc[0]
	else:
		allocation = patient_admission.append("facility_alloc")
	patient_admission.current_facility = facility
	allocation.bed = bed
	allocation.facility_type = facility_type
	allocation.facility = facility
	allocation.expected_discharge = expected_discharge
	if (occupied): #On Scheduled Status it may be occupied by any other patient
		allocation.patient_occupied = occupied #Done Admit : set to it True
	allocation.date_in = date_in
	allocation.time_in = time_in
	allocation.status = status
	allocation.facility_leaved = False
	patient_admission.save()

@frappe.whitelist()
def create_consultation(admission):
	patient_admission = frappe.get_doc("Patient Admission",admission)
	consultation = frappe.new_doc("Consultation")
	consultation.patient = patient_admission.patient
	consultation.physician = patient_admission.physician
	consultation.visit_department = patient_admission.visit_department
	consultation.patient_age = patient_admission.patient_age
	consultation.patient_sex = patient_admission.patient_sex
	consultation.symptoms = patient_admission.complaints
	consultation.vitals = patient_admission.vitals
	consultation.diagnosis = patient_admission.diagnosis
	consultation.admitted = True
	consultation.admission = admission
	return consultation.as_dict()

@frappe.whitelist()
def create_inv_for_facility_used(admission):
	patient_admission = frappe.get_doc("Patient Admission",admission)
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient_admission.patient, "customer")
	sales_invoice.physician = patient_admission.physician
	sales_invoice.due_date = getdate()

	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(patient_admission.patient, patient_admission.company)

	#Iterate for item and pass to the method
	for item_line in patient_admission.facility_alloc:
		item = frappe.get_doc("Item", item_line.facility_type)
		facility_type = frappe.get_doc("Facility Type", item_line.facility_type)
		day_hours = facility_type.per

		period_start = getdate(item_line.date_in)
		if(item_line.expected_discharge):
			period_end = getdate(item_line.expected_discharge)
		else:
			period_end = getdate()
		no_of_days = (period_end-period_start).days +1
		if(day_hours == "Day"):
			qty = no_of_days
		else:
			qty = no_of_days*24


		price_list = frappe.db.get ("Item Price",{"item_code":item.item_code})
		rate = price_list.price_list_rate

		create_sales_invoice_item_lines(item, sales_invoice, qty, rate)

	#income_account and cost_center in itemlines - by set_missing_values()
	sales_invoice.set_missing_values()
	return sales_invoice.as_dict()

def create_sales_invoice_item_lines(item, sales_invoice, qty, rate):
	sales_invoice_line = sales_invoice.append("items")
	sales_invoice_line.item_code = item.item_code
	sales_invoice_line.item_name =  item.item_name
	sales_invoice_line.qty = qty
	sales_invoice_line.rate = rate
	sales_invoice_line.description = item.description

@frappe.whitelist()
def create_discharge_summary(admission):
	patient_admission = frappe.get_doc("Patient Admission",admission)
	ds = frappe.new_doc("Discharge Summary")
	ds.patient = patient_admission.patient
	ds.physician = patient_admission.physician
	ds.visit_department = patient_admission.visit_department
	ds.patient_age = patient_admission.patient_age
	ds.patient_sex = patient_admission.patient_sex
	ds.admission = admission
	ds.admit_date = patient_admission.admit_date
	ds.discharge_date = patient_admission.discharge_date
	ds.save(ignore_permissions=True)
	frappe.db.set_value("Patient Admission", admission, "created_ds", True)

def disallocate_facility_bed(admission):
	patient_admission = frappe.get_doc("Patient Admission",admission)
	for allocation in patient_admission.facility_alloc:
		allocation.status = "Left"
	patient_admission.save()

def update_patient(patient, admission, admit):
	if(admit):
		frappe.db.sql("""update `tabPatient` set admitted=%s, admission=%s where name=%s""",(True,admission,patient))
	else:
		frappe.db.sql("""update `tabPatient` set admitted=%s, admission=%s where name=%s""",(False,None,patient))

def update_bed(bed, patient, admit):
	if(not admit):
		frappe.db.sql("""update `tabBed` set occupied=%s, patient=%s where patient=%s""",(False,None,patient))
	if(bed):
		frappe.db.sql("""update `tabBed` set occupied=%s, patient=%s where name=%s""",(True,patient,bed))

def update_facility(facility, patient, admit):
	if(facility):
		facility = frappe.get_doc("Facility",facility)
		if(admit):
			num_occupied = facility.num_occupied+1
		else:
			num_occupied = facility.num_occupied-1

		if(num_occupied == facility.num_beds):
			occupied = True
		else:
			occupied = False

		frappe.db.sql("""update `tabFacility` set num_occupied=%s, occupied=%s where name=%s""",(num_occupied,occupied,facility.name))
