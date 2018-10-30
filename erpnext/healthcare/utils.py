# -*- coding: utf-8 -*-
# Copyright (c) 2018, earthians and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
import math
from frappe.utils import time_diff_in_hours, rounded, getdate, add_days
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_income_account
from erpnext.healthcare.doctype.fee_validity.fee_validity import create_fee_validity, update_fee_validity
from erpnext.healthcare.doctype.lab_test.lab_test import create_multiple

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
							service_item = None
							if patient_appointment_obj.practitioner:
								service_item, practitioner_charge = service_item_and_practitioner_charge(patient_appointment_obj)
								income_account = get_income_account(patient_appointment_obj.practitioner, patient_appointment_obj.company)
							item_to_invoice.append({'reference_type': 'Patient Appointment', 'reference_name': patient_appointment_obj.name,
							'service': service_item, 'rate': practitioner_charge,
							'income_account': income_account})

			encounters = frappe.get_list("Patient Encounter", {'patient': patient.name, 'invoiced': False, 'docstatus': 1})
			if encounters:
				for encounter in encounters:
					encounter_obj = frappe.get_doc("Patient Encounter", encounter['name'])
					if not encounter_obj.appointment:
						practitioner_charge = 0
						income_account = None
						service_item = None
						if encounter_obj.practitioner:
							service_item, practitioner_charge = service_item_and_practitioner_charge(encounter_obj)
							income_account = get_income_account(encounter_obj.practitioner, encounter_obj.company)

						item_to_invoice.append({'reference_type': 'Patient Encounter', 'reference_name': encounter_obj.name,
						'service': service_item, 'rate': practitioner_charge,
						'income_account': income_account})

			lab_tests = frappe.get_list("Lab Test", {'patient': patient.name, 'invoiced': False})
			if lab_tests:
				for lab_test in lab_tests:
					lab_test_obj = frappe.get_doc("Lab Test", lab_test['name'])
					if frappe.db.get_value("Lab Test Template", lab_test_obj.template, "is_billable") == 1:
						item_to_invoice.append({'reference_type': 'Lab Test', 'reference_name': lab_test_obj.name,
						'service': frappe.db.get_value("Lab Test Template", lab_test_obj.template, "item")})

			lab_rxs = frappe.db.sql("""select lp.name from `tabPatient Encounter` et, `tabLab Prescription` lp
			where et.patient=%s and lp.parent=et.name and lp.lab_test_created=0 and lp.invoiced=0""", (patient.name))
			if lab_rxs:
				for lab_rx in lab_rxs:
					rx_obj = frappe.get_doc("Lab Prescription", lab_rx[0])
					if rx_obj.lab_test_code and (frappe.db.get_value("Lab Test Template", rx_obj.lab_test_code, "is_billable") == 1):
						item_to_invoice.append({'reference_type': 'Lab Prescription', 'reference_name': rx_obj.name,
						'service': frappe.db.get_value("Lab Test Template", rx_obj.lab_test_code, "item")})

			procedures = frappe.get_list("Clinical Procedure", {'patient': patient.name, 'invoiced': False})
			if procedures:
				for procedure in procedures:
					procedure_obj = frappe.get_doc("Clinical Procedure", procedure['name'])
					if not procedure_obj.appointment:
						if procedure_obj.procedure_template and (frappe.db.get_value("Clinical Procedure Template", procedure_obj.procedure_template, "is_billable") == 1):
							item_to_invoice.append({'reference_type': 'Clinical Procedure', 'reference_name': procedure_obj.name,
							'service': frappe.db.get_value("Clinical Procedure Template", procedure_obj.procedure_template, "item")})

			procedure_rxs = frappe.db.sql("""select pp.name from `tabPatient Encounter` et,
			`tabProcedure Prescription` pp where et.patient=%s and pp.parent=et.name and
			pp.procedure_created=0 and pp.invoiced=0 and pp.appointment_booked=0""", (patient.name))
			if procedure_rxs:
				for procedure_rx in procedure_rxs:
					rx_obj = frappe.get_doc("Procedure Prescription", procedure_rx[0])
					if frappe.db.get_value("Clinical Procedure Template", rx_obj.procedure, "is_billable") == 1:
						item_to_invoice.append({'reference_type': 'Procedure Prescription', 'reference_name': rx_obj.name,
						'service': frappe.db.get_value("Clinical Procedure Template", rx_obj.procedure, "item")})

			procedures = frappe.get_list("Clinical Procedure",
			{'patient': patient.name, 'invoice_separately_as_consumables': True, 'consumption_invoiced': False,
			'consume_stock': True, 'status': 'Completed'})
			if procedures:
				service_item = get_healthcare_service_item('clinical_procedure_consumable_item')
				if not service_item:
					msg = _(("Please Configure {0} in ").format("Clinical Procedure Consumable Item") \
						+ """<b><a href="#Form/Healthcare Settings">Healthcare Settings</a></b>""")
					frappe.throw(msg)
				for procedure in procedures:
					procedure_obj = frappe.get_doc("Clinical Procedure", procedure['name'])
					item_to_invoice.append({'reference_type': 'Clinical Procedure', 'reference_name': procedure_obj.name,
					'service': service_item, 'rate': procedure_obj.consumable_total_amount, 'description': procedure_obj.consumption_details})

			inpatient_services = frappe.db.sql("""select io.name, io.parent from `tabInpatient Record` ip,
			`tabInpatient Occupancy` io where ip.patient=%s and io.parent=ip.name and
			io.left=1 and io.invoiced=0""", (patient.name))
			if inpatient_services:
				for inpatient_service in inpatient_services:
					inpatient_occupancy = frappe.get_doc("Inpatient Occupancy", inpatient_service[0])
					service_unit_type = frappe.get_doc("Healthcare Service Unit Type", frappe.db.get_value("Healthcare Service Unit", inpatient_occupancy.service_unit, "service_unit_type"))
					if service_unit_type and service_unit_type.is_billable == 1:
						hours_occupied = time_diff_in_hours(inpatient_occupancy.check_out, inpatient_occupancy.check_in)
						qty = 0.5
						if hours_occupied > 0:
							actual_qty = hours_occupied / service_unit_type.no_of_hours
							floor = math.floor(actual_qty)
							decimal_part = actual_qty - floor
							if decimal_part > 0.5:
								qty = rounded(floor + 1, 1)
							elif decimal_part < 0.5 and decimal_part > 0:
								qty = rounded(floor + 0.5, 1)
							if qty <= 0:
								qty = 0.5
						item_to_invoice.append({'reference_type': 'Inpatient Occupancy', 'reference_name': inpatient_occupancy.name,
						'service': service_unit_type.item, 'qty': qty})

			return item_to_invoice
		else:
			frappe.throw(_("The Patient {0} do not have customer refrence to invoice").format(patient.name))

def service_item_and_practitioner_charge(doc):
	is_ip = doc_is_ip(doc)
	if is_ip:
		service_item = get_practitioner_service_item(doc.practitioner, "inpatient_visit_charge_item")
		if not service_item:
			service_item = get_healthcare_service_item("inpatient_visit_charge_item")
	else:
		service_item = get_practitioner_service_item(doc.practitioner, "op_consulting_charge_item")
		if not service_item:
			service_item = get_healthcare_service_item("op_consulting_charge_item")
	if not service_item:
		throw_config_service_item(is_ip)

	practitioner_charge = get_practitioner_charge(doc.practitioner, is_ip)
	if not practitioner_charge:
		throw_config_practitioner_charge(is_ip, doc.practitioner)

	return service_item, practitioner_charge

def throw_config_service_item(is_ip):
	service_item_lable = "Out Patient Consulting Charge Item"
	if is_ip:
		service_item_lable = "Inpatient Visit Charge Item"

	msg = _(("Please Configure {0} in ").format(service_item_lable) \
		+ """<b><a href="#Form/Healthcare Settings">Healthcare Settings</a></b>""")
	frappe.throw(msg)

def throw_config_practitioner_charge(is_ip, practitioner):
	charge_name = "OP Consulting Charge"
	if is_ip:
		charge_name = "Inpatient Visit Charge"

	msg = _(("Please Configure {0} for Healthcare Practitioner").format(charge_name) \
		+ """ <b><a href="#Form/Healthcare Practitioner/{0}">{0}</a></b>""".format(practitioner))
	frappe.throw(msg)

def get_practitioner_service_item(practitioner, service_item_field):
	return frappe.db.get_value("Healthcare Practitioner", practitioner, service_item_field)

def get_healthcare_service_item(service_item_field):
	return frappe.db.get_value("Healthcare Settings", None, service_item_field)

def doc_is_ip(doc):
	is_ip = False
	if doc.inpatient_record:
		is_ip = True
	return is_ip

def get_practitioner_charge(practitioner, is_ip):
	if is_ip:
		practitioner_charge = frappe.db.get_value("Healthcare Practitioner", practitioner, "inpatient_visit_charge")
	else:
		practitioner_charge = frappe.db.get_value("Healthcare Practitioner", practitioner, "op_consulting_charge")
	if practitioner_charge:
		return practitioner_charge
	return False

def manage_invoice_submit_cancel(doc, method):
	if doc.items:
		for item in doc.items:
			if item.get("reference_dt") and item.get("reference_dn"):
				if frappe.get_meta(item.reference_dt).has_field("invoiced"):
					set_invoiced(item, method, doc.name)

	if method=="on_submit" and frappe.db.get_value("Healthcare Settings", None, "create_test_on_si_submit") == '1':
		create_multiple("Sales Invoice", doc.name)

def set_invoiced(item, method, ref_invoice=None):
	invoiced = False
	if(method=="on_submit"):
		validate_invoiced_on_submit(item)
		invoiced = True

	if item.reference_dt == 'Clinical Procedure':
		if get_healthcare_service_item('clinical_procedure_consumable_item') == item.item_code:
			frappe.db.set_value(item.reference_dt, item.reference_dn, "consumption_invoiced", invoiced)
		else:
			frappe.db.set_value(item.reference_dt, item.reference_dn, "invoiced", invoiced)
	else:
		frappe.db.set_value(item.reference_dt, item.reference_dn, "invoiced", invoiced)

	if item.reference_dt == 'Patient Appointment':
		if frappe.db.get_value('Patient Appointment', item.reference_dn, 'procedure_template'):
			dt_from_appointment = "Clinical Procedure"
		else:
			manage_fee_validity(item.reference_dn, method, ref_invoice)
			dt_from_appointment = "Patient Encounter"
		manage_doc_for_appoitnment(dt_from_appointment, item.reference_dn, invoiced)

	elif item.reference_dt == 'Lab Prescription':
		manage_prescriptions(invoiced, item.reference_dt, item.reference_dn, "Lab Test", "lab_test_created")

	elif item.reference_dt == 'Procedure Prescription':
		manage_prescriptions(invoiced, item.reference_dt, item.reference_dn, "Clinical Procedure", "procedure_created")

def validate_invoiced_on_submit(item):
	if item.reference_dt == 'Clinical Procedure' and get_healthcare_service_item('clinical_procedure_consumable_item') == item.item_code:
			is_invoiced = frappe.db.get_value(item.reference_dt, item.reference_dn, "consumption_invoiced")
	else:
		is_invoiced = frappe.db.get_value(item.reference_dt, item.reference_dn, "invoiced")
	if is_invoiced == 1:
		frappe.throw(_("The item referenced by {0} - {1} is already invoiced"\
		).format(item.reference_dt, item.reference_dn))

def manage_prescriptions(invoiced, ref_dt, ref_dn, dt, created_check_field):
	created = frappe.db.get_value(ref_dt, ref_dn, created_check_field)
	if created == 1:
		# Fetch the doc created for the prescription
		doc_created = frappe.db.get_value(dt, {'prescription': ref_dn})
		frappe.db.set_value(dt, doc_created, 'invoiced', invoiced)

def validity_exists(practitioner, patient):
	return frappe.db.exists({
			"doctype": "Fee Validity",
			"practitioner": practitioner,
			"patient": patient})

def manage_fee_validity(appointment_name, method, ref_invoice=None):
	appointment_doc = frappe.get_doc("Patient Appointment", appointment_name)
	validity_exist = validity_exists(appointment_doc.practitioner, appointment_doc.patient)
	do_not_update = False
	visited = 0
	if validity_exist:
		fee_validity = frappe.get_doc("Fee Validity", validity_exist[0][0])
		# Check if the validity is valid
		if (fee_validity.valid_till >= appointment_doc.appointment_date):
			if (method == "on_cancel" and appointment_doc.status != "Closed"):
				if ref_invoice == fee_validity.ref_invoice:
					visited = fee_validity.visited - 1
					if visited < 0:
						visited = 0
					frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				do_not_update = True
			elif (method == "on_submit" and fee_validity.visited < fee_validity.max_visit):
				visited = fee_validity.visited + 1
				frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				do_not_update = True
			else:
				do_not_update = False

		if not do_not_update:
			fee_validity = update_fee_validity(fee_validity, appointment_doc.appointment_date, ref_invoice)
			visited = fee_validity.visited
	else:
		fee_validity = create_fee_validity(appointment_doc.practitioner, appointment_doc.patient, appointment_doc.appointment_date, ref_invoice)
		visited = fee_validity.visited

	# Mark All Patient Appointment invoiced = True in the validity range do not cross the max visit
	if (method == "on_cancel"):
		invoiced = True
	else:
		invoiced = False

	patient_appointments = appointments_valid_in_fee_validity(appointment_doc, invoiced)
	if patient_appointments and fee_validity:
		visit = visited
		for appointment in patient_appointments:
			if (method == "on_cancel" and appointment.status != "Closed"):
				if ref_invoice == fee_validity.ref_invoice:
					visited = visited - 1
					if visited < 0:
						visited = 0
					frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				frappe.db.set_value("Patient Appointment", appointment.name, "invoiced", False)
				manage_doc_for_appoitnment("Patient Encounter", appointment.name, False)
			elif method == "on_submit" and int(fee_validity.max_visit) > visit:
				if ref_invoice == fee_validity.ref_invoice:
					visited = visited + 1
					frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				frappe.db.set_value("Patient Appointment", appointment.name, "invoiced", True)
				manage_doc_for_appoitnment("Patient Encounter", appointment.name, True)
			if ref_invoice == fee_validity.ref_invoice:
				visit = visit + 1

	if method == "on_cancel":
		ref_invoice_in_fee_validity = frappe.db.get_value("Fee Validity", fee_validity.name, 'ref_invoice')
		if ref_invoice_in_fee_validity == ref_invoice:
			frappe.delete_doc("Fee Validity", fee_validity.name)

def appointments_valid_in_fee_validity(appointment, invoiced):
	valid_days = frappe.db.get_value("Healthcare Settings", None, "valid_days")
	max_visit = frappe.db.get_value("Healthcare Settings", None, "max_visit")
	if int(max_visit) < 1:
		max_visit = 1
	valid_days_date = add_days(getdate(appointment.appointment_date), int(valid_days))
	return frappe.get_list("Patient Appointment",{'patient': appointment.patient, 'invoiced': invoiced,
	'appointment_date':("<=", valid_days_date), 'appointment_date':(">=", getdate(appointment.appointment_date)),
	'practitioner': appointment.practitioner}, order_by="appointment_date", limit=int(max_visit)-1)

def manage_doc_for_appoitnment(dt_from_appointment, appointment, invoiced):
	dn_from_appointment = frappe.db.exists(
		dt_from_appointment,
		{
			"appointment": appointment
		}
	)
	if dn_from_appointment:
		frappe.db.set_value(dt_from_appointment, dn_from_appointment, "invoiced", invoiced)

@frappe.whitelist()
def get_drugs_to_invoice(encounter):
	encounter = frappe.get_doc("Patient Encounter", encounter)
	if encounter:
		patient = frappe.get_doc("Patient", encounter.patient)
		if patient and patient.customer:
				item_to_invoice = []
				for drug_line in encounter.drug_prescription:
					if drug_line.drug_code:
						qty = 1
						if frappe.db.get_value("Item", drug_line.drug_code, "stock_uom") == "Nos":
							qty = drug_line.get_quantity()
						description = False
						if drug_line.dosage:
							description = drug_line.dosage
						if description and drug_line.period:
							description += " for "+drug_line.period
						if not description:
							description = ""
						item_to_invoice.append({'drug_code': drug_line.drug_code, 'quantity': qty,
						'description': description})
				return item_to_invoice

@frappe.whitelist()
def get_children(doctype, parent, company, is_root=False):
	parent_fieldname = 'parent_' + doctype.lower().replace(' ', '_')
	fields = [
		'name as value',
		'is_group as expandable',
		'lft',
		'rgt'
	]
	# fields = [ 'name', 'is_group', 'lft', 'rgt' ]
	filters = [['ifnull(`{0}`,"")'.format(parent_fieldname), '=', '' if is_root else parent]]

	if is_root:
		fields += ['service_unit_type'] if doctype == 'Healthcare Service Unit' else []
		filters.append(['company', '=', company])

	else:
		fields += ['service_unit_type', 'allow_appointments', 'inpatient_occupancy', 'occupancy_status'] if doctype == 'Healthcare Service Unit' else []
		fields += [parent_fieldname + ' as parent']

	hc_service_units = frappe.get_list(doctype, fields=fields, filters=filters)

	if doctype == 'Healthcare Service Unit':
		for each in hc_service_units:
			occupancy_msg = ""
			if each['expandable'] == 1:
				occupied = False
				vacant = False
				child_list = frappe.db.sql("""
					select name, occupancy_status from `tabHealthcare Service Unit`
					where inpatient_occupancy = 1 and
					lft > %s and rgt < %s""",
					(each['lft'], each['rgt']))
				for child in child_list:
					if not occupied:
						occupied = 0
					if child[1] == "Occupied":
						occupied += 1
					if not vacant:
						vacant = 0
					if child[1] == "Vacant":
						vacant += 1
				if vacant and occupied:
					occupancy_total = vacant+occupied
					occupancy_msg = str(occupied) + " Occupied out of " + str(occupancy_total)
			each["occupied_out_of_vacant"] = occupancy_msg
	return hc_service_units
