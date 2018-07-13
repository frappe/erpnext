# -*- coding: utf-8 -*-
# Copyright (c) 2018, earthians and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
from frappe.utils import date_diff, getdate
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_income_account
from erpnext.healthcare.doctype.patient_appointment.patient_appointment import validity_exists
from erpnext.healthcare.doctype.fee_validity.fee_validity import create_fee_validity, update_fee_validity

@frappe.whitelist()
def get_healthcare_services_to_invoice(patient):
	patient = frappe.get_doc("Patient", patient)
	if patient:
		if patient.customer:
			item_to_invoice = []
			patient_appointments = frappe.get_list("Patient Appointment",{'patient': patient.name, 'invoiced': False},
			order_by="appointment_date")
			if patient_appointments:
				fee_validity_details = []
				valid_days = frappe.db.get_value("Healthcare Settings", None, "valid_days")
				max_visit = frappe.db.get_value("Healthcare Settings", None, "max_visit")
				for patient_appointment in patient_appointments:
					patient_appointment_obj = frappe.get_doc("Patient Appointment", patient_appointment['name'])

					if patient_appointment_obj.procedure_template:
						if frappe.db.get_value("Clinical Procedure Template", patient_appointment_obj.procedure_template, "is_billable") == 1:
							item_to_invoice.append({'reference_type': 'Patient Appointment', 'reference_name': patient_appointment_obj.name, 'service': patient_appointment_obj.procedure_template})
					else:
						practitioner_exist_in_list = False
						skip_invoice = False
						if fee_validity_details:
							for validity in fee_validity_details:
								if validity['practitioner'] == patient_appointment_obj.practitioner:
									practitioner_exist_in_list = True
									if validity['valid_till'] >= patient_appointment_obj.appointment_date:
										validity['visits'] = validity['visits']+1
										if int(max_visit) > validity['visits']:
											skip_invoice = True
									if not skip_invoice:
										validity['visits'] = 1
										validity['valid_till'] = patient_appointment_obj.appointment_date + datetime.timedelta(days=int(valid_days))
						if not practitioner_exist_in_list:
							valid_till = patient_appointment_obj.appointment_date + datetime.timedelta(days=int(valid_days))
							visits = 0
							validity_exist = validity_exists(patient_appointment_obj.practitioner, patient_appointment_obj.patient)
							if validity_exist:
								fee_validity = frappe.get_doc("Fee Validity", validity_exist[0][0])
								valid_till = fee_validity.valid_till
								visits = fee_validity.visited
							fee_validity_details.append({'practitioner': patient_appointment_obj.practitioner,
							'valid_till': valid_till, 'visits': visits})

						if not skip_invoice:
							practitioner_charge = 0
							income_account = None
							if patient_appointment_obj.practitioner:
								practitioner_charge = get_practitioner_charge(patient_appointment_obj.practitioner)
								income_account = get_income_account(patient_appointment_obj.practitioner, patient_appointment_obj.company)
							item_to_invoice.append({'reference_type': 'Patient Appointment', 'reference_name': patient_appointment_obj.name,
							'service': 'Consulting Charges', 'rate': practitioner_charge,
							'income_account': income_account})

			encounters = frappe.get_list("Patient Encounter", {'patient': patient.name, 'invoiced': False, 'docstatus': 1})
			if encounters:
				for encounter in encounters:
					encounter_obj = frappe.get_doc("Patient Encounter", encounter['name'])
					if not encounter_obj.appointment:
						practitioner_charge = 0
						income_account = None
						if encounter_obj.practitioner:
							practitioner_charge = get_practitioner_charge(encounter_obj.practitioner)
							income_account = get_income_account(encounter_obj.practitioner, encounter_obj.company)
						item_to_invoice.append({'reference_type': 'Patient Encounter', 'reference_name': encounter_obj.name,
						'service': 'Consulting Charges', 'rate': practitioner_charge,
						'income_account': income_account})

			lab_tests = frappe.get_list("Lab Test", {'patient': patient.name, 'invoiced': False})
			if lab_tests:
				for lab_test in lab_tests:
					lab_test_obj = frappe.get_doc("Lab Test", lab_test['name'])
					if frappe.db.get_value("Lab Test Template", lab_test_obj.template, "is_billable") == 1:
						item_to_invoice.append({'reference_type': 'Lab Test', 'reference_name': lab_test_obj.name, 'service': lab_test_obj.template})

			lab_rxs = frappe.db.sql("""select lp.name from `tabPatient Encounter` et,
			`tabLab Prescription` lp where et.patient=%s and lp.parent=et.name and lp.test_created=0 and lp.invoiced=0""", (patient.name))
			if lab_rxs:
				for lab_rx in lab_rxs:
					rx_obj = frappe.get_doc("Lab Prescription", lab_rx[0])
					if rx_obj.test_code and (frappe.db.get_value("Lab Test Template", rx_obj.test_code, "is_billable") == 1):
						item_to_invoice.append({'reference_type': 'Lab Prescription', 'reference_name': rx_obj.name, 'service': rx_obj.test_code})

			procedures = frappe.get_list("Clinical Procedure", {'patient': patient.name, 'invoiced': False})
			if procedures:
				for procedure in procedures:
					procedure_obj = frappe.get_doc("Clinical Procedure", procedure['name'])
					if not procedure_obj.appointment:
						if procedure_obj.procedure_template and (frappe.db.get_value("Clinical Procedure Template", procedure_obj.procedure_template, "is_billable") == 1):
							item_to_invoice.append({'reference_type': 'Clinical Procedure', 'reference_name': procedure_obj.name, 'service': procedure_obj.procedure_template})

			procedure_rxs = frappe.db.sql("""select pp.name from `tabPatient Encounter` et,
			`tabProcedure Prescription` pp where et.patient=%s and pp.parent=et.name and
			pp.procedure_created=0 and pp.invoiced=0 and pp.appointment_booked=0""", (patient.name))
			if procedure_rxs:
				for procedure_rx in procedure_rxs:
					rx_obj = frappe.get_doc("Procedure Prescription", procedure_rx[0])
					if frappe.db.get_value("Clinical Procedure Template", rx_obj.procedure, "is_billable") == 1:
						item_to_invoice.append({'reference_type': 'Procedure Prescription', 'reference_name': rx_obj.name, 'service': rx_obj.procedure})

			procedure_consumables = frappe.db.sql("""select pc.name from `tabClinical Procedure` cp,
			`tabClinical Procedure Item` pc where cp.patient=%s and pc.parent=cp.name and
			pc.invoice_separately_as_consumables=1 and pc.invoiced=0""", (patient.name))
			if procedure_consumables:
				for procedure_consumable in procedure_consumables:
					procedure_consumable_obj = frappe.get_doc("Clinical Procedure Item", procedure_consumable[0])
					item_to_invoice.append({'reference_type': 'Clinical Procedure Item', 'reference_name': procedure_consumable_obj.name,
					'service': procedure_consumable_obj.item_code, 'qty': procedure_consumable_obj.qty})

			inpatient_services = frappe.db.sql("""select io.name, io.parent from `tabInpatient Record` ip,
			`tabInpatient Occupancy` io where ip.patient=%s and io.parent=ip.name and
			io.left=1 and io.invoiced=0""", (patient.name))
			if inpatient_services:
				for inpatient_service in inpatient_services:
					inpatient_occupancy = frappe.get_doc("Inpatient Occupancy", inpatient_service[0])
					service_unit_type = frappe.get_doc("Healthcare Service Unit Type", frappe.db.get_value("Healthcare Service Unit", inpatient_occupancy.service_unit, "service_unit_type"))
					if service_unit_type and service_unit_type.is_billable == 1:
						qty = date_diff(getdate(inpatient_occupancy.check_out), getdate(inpatient_occupancy.check_in))
						if qty < 1:
							qty = 1
						item_to_invoice.append({'reference_type': 'Inpatient Occupancy', 'reference_name': inpatient_occupancy.name,
						'service': service_unit_type.item, 'qty': qty})

			return item_to_invoice
		else:
			frappe.throw(_("The Patient {0} do not have customer refrence to invoice").format(patient.name))

def get_practitioner_charge(practitioner):
	practitioner_charge = frappe.db.get_value("Healthcare Practitioner", practitioner, "op_consulting_charge")
	if practitioner_charge:
		return practitioner_charge

def manage_invoice_submit_cancel(doc, method):
	if doc.items:
		for item in doc.items:
			if item.reference_dt and item.reference_dn:
				if frappe.get_meta(item.reference_dt).has_field("invoiced"):
					set_invoiced(item, method)

def set_invoiced(item, method):
	invoiced = False
	if(method=="on_submit"):
		validate_invoiced_on_submit(item)
		invoiced = True

	frappe.db.set_value(item.reference_dt, item.reference_dn, "invoiced", invoiced)
	if item.reference_dt == 'Patient Appointment':
		if frappe.db.get_value('Patient Appointment', item.reference_dn, 'procedure_template'):
			dt_from_appointment = "Clinical Procedure"
		else:
			manage_fee_validity(item.reference_dn, method)
			dt_from_appointment = "Patient Encounter"
		manage_doc_for_appoitnment(dt_from_appointment, item.reference_dn, invoiced)

	elif item.reference_dt == 'Lab Prescription':
		manage_prescriptions(invoiced, item.reference_dt, item.reference_dn, "Lab Test", "test_created")

	elif item.reference_dt == 'Procedure Prescription':
		manage_prescriptions(invoiced, item.reference_dt, item.reference_dn, "Clinical Procedure", "procedure_created")

def validate_invoiced_on_submit(item):
	is_invoiced = frappe.db.get_value(item.reference_dt, item.reference_dn, "invoiced")
	if is_invoiced == 1:
		frappe.throw(_("The item referenced by {0} - {1} is already invoiced"\
		).format(item.reference_dt, item.reference_dn))

def manage_prescriptions(invoiced, ref_dt, ref_dn, dt, created_check_field):
	created = frappe.db.get_value(ref_dt, ref_dn, created_check_field)
	if created == 1:
		# Fetch the doc created for the prescription
		doc_created = frappe.db.get_value(dt, {'prescription': item.reference_dn})
		frappe.db.set_value(dt, doc_created, 'invoiced', invoiced)

def manage_fee_validity(appointment_name, method):
	appointment_doc = frappe.get_doc("Patient Appointment", appointment_name)
	validity_exist = validity_exists(appointment_doc.practitioner, appointment_doc.patient)
	do_not_update = False
	visited = 0
	if validity_exist:
		fee_validity = frappe.get_doc("Fee Validity", validity_exist[0][0])
		# Check if the validity is valid
		if (fee_validity.valid_till >= appointment_doc.appointment_date):
			if (method == "on_cancel" and appointment_doc.status != "Closed"):
				visited = fee_validity.visited - 1
				if visited < 0:
					visited = 0
				frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				do_not_update = True
			elif (fee_validity.visited < fee_validity.max_visit):
				visited = fee_validity.visited + 1
				frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				do_not_update = True
			else:
				do_not_update = False

		if not do_not_update:
			fee_validity = update_fee_validity(fee_validity, appointment_doc.appointment_date)
			visited = fee_validity.visited
	else:
		fee_validity = create_fee_validity(appointment_doc.practitioner, appointment_doc.patient, appointment_doc.appointment_date)
		visited = fee_validity.visited

	# Mark All Patient Appointment invoiced = True in the validity range do not cross the max visit
	if (method == "on_cancel"):
		invoiced = True
	else:
		invoiced = False
	patient_appointments = frappe.get_list("Patient Appointment",{'patient': fee_validity.patient, 'invoiced': invoiced,
	'appointment_date':("<=", fee_validity.valid_till), 'practitioner': fee_validity.practitioner}, order_by="appointment_date")
	if patient_appointments and fee_validity:
		visit = visited
		for appointment in patient_appointments:
			if (method == "on_cancel" and appointment.status != "Closed"):
				visited = visited - 1
				if visited < 0:
					visited = 0
				frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				frappe.db.set_value("Patient Appointment", appointment.name, "invoiced", False)
				manage_doc_for_appoitnment("Patient Encounter", appointment.name, False)
			elif int(fee_validity.max_visit) > visit:
				visited = visited + 1
				frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				frappe.db.set_value("Patient Appointment", appointment.name, "invoiced", True)
				manage_doc_for_appoitnment("Patient Encounter", appointment.name, True)
			visit = visit + 1

def manage_doc_for_appoitnment(dt_from_appointment, appointment, invoiced):
	dn_from_appointment = frappe.db.exists(
		dt_from_appointment,
		{
			"appointment": appointment
		}
	)
	if dn_from_appointment:
		frappe.db.set_value(dt_from_appointment, dn_from_appointment, "invoiced", invoiced)
