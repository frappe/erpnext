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
	patient = frappe.get_doc('Patient', patient)
	if patient:
		validate_customer_created(patient)
		items_to_invoice = []
		patient_appointments = frappe.get_list(
			'Patient Appointment',
			fields='*',
			filters={'patient': patient.name, 'invoiced': False},
			order_by='appointment_date'
		)
		if patient_appointments:
			items_to_invoice = get_fee_validity(patient_appointments)

		encounters = get_encounters_to_invoice(patient)
		lab_tests = get_lab_tests_to_invoice(patient)
		clinical_procedures = get_clinical_procedures_to_invoice(patient)
		inpatient_services = get_inpatient_services_to_invoice(patient)

		items_to_invoice = encounters + lab_tests + clinical_procedures + inpatient_services
		return items_to_invoice

def validate_customer_created(patient):
	if not frappe.db.get_value('Patient', patient.name, 'customer'):
		msg = _("Please set a Customer linked to the Patient")
		msg +=  " <b><a href='#Form/Patient/{0}'>{0}</a></b>".format(patient.name)
		frappe.throw(msg, title=_('Customer Not Found'))

def get_fee_validity(patient_appointments):
	fee_validity_details = []
	items_to_invoice = []
	valid_days = frappe.db.get_single_value('Healthcare Settings', 'valid_days')
	max_visits = frappe.db.get_single_value('Healthcare Settings', 'max_visits')
	for appointment in patient_appointments:
		if appointment.procedure_template:
			if frappe.db.get_value('Clinical Procedure Template', appointment.procedure_template, 'is_billable'):
				items_to_invoice.append({
					'reference_type': 'Patient Appointment',
					'reference_name': appointment.name,
					'service': appointment.procedure_template
				})
		else:
			practitioner_exist_in_list = False
			skip_invoice = False
			if fee_validity_details:
				for validity in fee_validity_details:
					if validity['practitioner'] == appointment.practitioner:
						practitioner_exist_in_list = True
						if validity['valid_till'] >= appointment.appointment_date:
							validity['visits'] = validity['visits'] + 1
							if int(max_visits) > validity['visits']:
								skip_invoice = True
						if not skip_invoice:
							validity['visits'] = 1
							validity['valid_till'] = appointment.appointment_date + datetime.timedelta(days=int(valid_days))

			if not practitioner_exist_in_list:
				valid_till = appointment.appointment_date + datetime.timedelta(days=int(valid_days))
				visits = 0
				validity = check_validity_exists(appointment.practitioner, appointment.patient)
				if validity:
					fee_validity = frappe.get_doc('Fee Validity', validity)
					valid_till = fee_validity.valid_till
					visits = fee_validity.visited
				fee_validity_details.append({'practitioner': appointment.practitioner,
				'valid_till': valid_till, 'visits': visits})

			if not skip_invoice:
				practitioner_charge = 0
				income_account = None
				service_item = None
				if appointment.practitioner:
					service_item, practitioner_charge = get_service_item_and_practitioner_charge(appointment)
					income_account = get_income_account(appointment.practitioner, appointment.company)
				items_to_invoice.append({'reference_type': 'Patient Appointment', 'reference_name': appointment.name,
				'service': service_item, 'rate': practitioner_charge,
				'income_account': income_account})

	return items_to_invoice


def get_encounters_to_invoice(patient):
	encounters_to_invoice = []
	encounters = frappe.get_list(
		'Patient Encounter',
		fields=['*'],
		filters={'patient': patient.name, 'invoiced': False, 'docstatus': 1}
	)
	if encounters:
		for encounter in encounters:
			if not encounter.appointment:
				practitioner_charge = 0
				income_account = None
				service_item = None
				if encounter.practitioner:
					service_item, practitioner_charge = get_service_item_and_practitioner_charge(encounter)
					income_account = get_income_account(encounter.practitioner, encounter.company)

				encounters_to_invoice.append({
					'reference_type': 'Patient Encounter',
					'reference_name': encounter.name,
					'service': service_item,
					'rate': practitioner_charge,
					'income_account': income_account
				})

	return encounters_to_invoice


def get_lab_tests_to_invoice(patient):
	lab_tests_to_invoice = []
	lab_tests = frappe.get_list(
		'Lab Test',
		fields=['name', 'template'],
		filters={'patient': patient.name, 'invoiced': False, 'docstatus': 1}
	)
	for lab_test in lab_tests:
		if frappe.db.get_value('Lab Test Template', lab_test.template, 'is_billable'):
			lab_tests_to_invoice.append({
				'reference_type': 'Lab Test',
				'reference_name': lab_test.name,
				'service': frappe.db.get_value('Lab Test Template', lab_test.template, 'item')
			})

	lab_prescriptions = frappe.db.sql('''select lp.name, lp.lab_test_code from `tabPatient Encounter` et, `tabLab Prescription` lp
	where et.patient=%s and lp.parent=et.name and lp.lab_test_created=0 and lp.invoiced=0''', (patient.name), as_dict=1)

	for prescription in lab_prescriptions:
		if prescription.lab_test_code and frappe.db.get_value('Lab Test Template', prescription.lab_test_code, 'is_billable'):
			lab_tests_to_invoice.append({
				'reference_type': 'Lab Prescription',
				'reference_name': prescription.name,
				'service': frappe.db.get_value('Lab Test Template', prescription.lab_test_code, 'item')
			})

	return lab_tests_to_invoice


def get_clinical_procedures_to_invoice(patient):
	clinical_procedures_to_invoice = []
	procedures = frappe.get_list(
		'Clinical Procedure',
		fields='*',
		filters={'patient': patient.name, 'invoiced': False}
	)
	for procedure in procedures:
		if not procedure.appointment:
			if procedure.procedure_template and frappe.db.get_value('Clinical Procedure Template', procedure.procedure_template, 'is_billable'):
				clinical_procedures_to_invoice.append({
					'reference_type': 'Clinical Procedure',
					'reference_name': procedure.name,
					'service': frappe.db.get_value('Clinical Procedure Template', procedure.procedure_template, 'item')
				})

		# consumables
		if procedure.invoice_separately_as_consumables and procedure.consume_stock \
			and procedure.status == 'Completed' and not procedure.consumption_invoiced:

			service_item = get_healthcare_service_item('clinical_procedure_consumable_item')
			if not service_item:
				msg = _('Please Configure Clinical Procedure Consumable Item in ')
				msg += '''<b><a href='#Form/Healthcare Settings'>Healthcare Settings</a></b>'''
				frappe.throw(msg, title=_('Missing Configuration'))

			clinical_procedures_to_invoice.append({
				'reference_type': 'Clinical Procedure',
				'reference_name': procedure.name,
				'service': service_item,
				'rate': procedure.consumable_total_amount,
				'description': procedure.consumption_details
			})

	procedure_prescriptions = frappe.db.sql('''select pp.name, pp.procedure from `tabPatient Encounter` et,
	`tabProcedure Prescription` pp where et.patient=%s and pp.parent=et.name and
	pp.procedure_created=0 and pp.invoiced=0 and pp.appointment_booked=0''', (patient.name), as_dict=1)

	for prescription in procedure_prescriptions:
		if frappe.db.get_value('Clinical Procedure Template', prescription.procedure, 'is_billable'):
			items_to_invoice.append({
				'reference_type': 'Procedure Prescription',
				'reference_name': prescription.name,
				'service': frappe.db.get_value('Clinical Procedure Template', prescription.procedure, 'item')
			})

	return clinical_procedures_to_invoice


def get_inpatient_services_to_invoice(patient):
	services_to_invoice = []
	inpatient_services = frappe.db.sql('''select io.* from `tabInpatient Record` ip,
	`tabInpatient Occupancy` io where ip.patient=%s and io.parent=ip.name and
	io.left=1 and io.invoiced=0''', (patient.name), as_dict=1)

	for inpatient_occupancy in inpatient_services:
		service_unit_type = frappe.db.get_value('Healthcare Service Unit', inpatient_occupancy.service_unit, 'service_unit_type')
		service_unit_type = frappe.get_doc('Healthcare Service Unit Type', service_unit_type)
		if service_unit_type and service_unit_type.is_billable:
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
			services_to_invoice.append({
				'reference_type': 'Inpatient Occupancy',
				'reference_name': inpatient_occupancy.name,
				'service': service_unit_type.item, 'qty': qty
			})

	return services_to_invoice


def get_service_item_and_practitioner_charge(doc):
	is_inpatient = doc.inpatient_record
	if is_inpatient:
		service_item = get_practitioner_service_item(doc.practitioner, 'inpatient_visit_charge_item')
		if not service_item:
			service_item = get_healthcare_service_item('inpatient_visit_charge_item')
	else:
		service_item = get_practitioner_service_item(doc.practitioner, 'op_consulting_charge_item')
		if not service_item:
			service_item = get_healthcare_service_item('op_consulting_charge_item')
	if not service_item:
		throw_config_service_item(is_inpatient)

	practitioner_charge = get_practitioner_charge(doc.practitioner, is_inpatient)
	if not practitioner_charge:
		throw_config_practitioner_charge(is_inpatient, doc.practitioner)

	return service_item, practitioner_charge


def throw_config_service_item(is_inpatient):
	service_item_lable = 'Out Patient Consulting Charge Item'
	if is_inpatient:
		service_item_lable = 'Inpatient Visit Charge Item'

	msg = _(('Please Configure {0} in ').format(service_item_lable) \
		+ '''<b><a href='#Form/Healthcare Settings'>Healthcare Settings</a></b>''')
	frappe.throw(msg, title=_('Missing Configuration'))


def throw_config_practitioner_charge(is_inpatient, practitioner):
	charge_name = 'OP Consulting Charge'
	if is_inpatient:
		charge_name = 'Inpatient Visit Charge'

	msg = _(('Please Configure {0} for Healthcare Practitioner').format(charge_name) \
		+ ''' <b><a href='#Form/Healthcare Practitioner/{0}'>{0}</a></b>'''.format(practitioner))
	frappe.throw(msg, title=_('Missing Configuration'))


def get_practitioner_service_item(practitioner, service_item_field):
	return frappe.db.get_value('Healthcare Practitioner', practitioner, service_item_field)


def get_healthcare_service_item(service_item_field):
	return frappe.db.get_single_value('Healthcare Settings', service_item_field)


def get_practitioner_charge(practitioner, is_inpatient):
	if is_inpatient:
		practitioner_charge = frappe.db.get_value('Healthcare Practitioner', practitioner, 'inpatient_visit_charge')
	else:
		practitioner_charge = frappe.db.get_value('Healthcare Practitioner', practitioner, 'op_consulting_charge')
	if practitioner_charge:
		return practitioner_charge
	return False


def manage_invoice_submit_cancel(doc, method):
	if doc.items:
		for item in doc.items:
			if item.get('reference_dt') and item.get('reference_dn'):
				if frappe.get_meta(item.reference_dt).has_field('invoiced'):
					set_invoiced(item, method, doc.name)

	if method=='on_submit' and frappe.db.get_single_value('Healthcare Settings', 'create_lab_test_on_si_submit'):
		create_multiple('Sales Invoice', doc.name)


def set_invoiced(item, method, ref_invoice=None):
	invoiced = False
	if method=='on_submit':
		validate_invoiced_on_submit(item)
		invoiced = True

	if item.reference_dt == 'Clinical Procedure':
		if get_healthcare_service_item('clinical_procedure_consumable_item') == item.item_code:
			frappe.db.set_value(item.reference_dt, item.reference_dn, 'consumption_invoiced', invoiced)
		else:
			frappe.db.set_value(item.reference_dt, item.reference_dn, 'invoiced', invoiced)
	else:
		frappe.db.set_value(item.reference_dt, item.reference_dn, 'invoiced', invoiced)

	if item.reference_dt == 'Patient Appointment':
		if frappe.db.get_value('Patient Appointment', item.reference_dn, 'procedure_template'):
			dt_from_appointment = 'Clinical Procedure'
		else:
			manage_fee_validity(item.reference_dn, method, ref_invoice)
			dt_from_appointment = 'Patient Encounter'
		manage_doc_for_appointment(dt_from_appointment, item.reference_dn, invoiced)

	elif item.reference_dt == 'Lab Prescription':
		manage_prescriptions(invoiced, item.reference_dt, item.reference_dn, 'Lab Test', 'lab_test_created')

	elif item.reference_dt == 'Procedure Prescription':
		manage_prescriptions(invoiced, item.reference_dt, item.reference_dn, 'Clinical Procedure', 'procedure_created')


def validate_invoiced_on_submit(item):
	if item.reference_dt == 'Clinical Procedure' and get_healthcare_service_item('clinical_procedure_consumable_item') == item.item_code:
		is_invoiced = frappe.db.get_value(item.reference_dt, item.reference_dn, 'consumption_invoiced')
	else:
		is_invoiced = frappe.db.get_value(item.reference_dt, item.reference_dn, 'invoiced')
	if is_invoiced:
		frappe.throw(_('The item referenced by {0} - {1} is already invoiced'\
		).format(item.reference_dt, item.reference_dn))


def manage_prescriptions(invoiced, ref_dt, ref_dn, dt, created_check_field):
	created = frappe.db.get_value(ref_dt, ref_dn, created_check_field)
	if created:
		# Fetch the doc created for the prescription
		doc_created = frappe.db.get_value(dt, {'prescription': ref_dn})
		frappe.db.set_value(dt, doc_created, 'invoiced', invoiced)


def check_validity_exists(practitioner, patient):
	return frappe.db.get_value('Fee Validity', {'practitioner': practitioner, 'patient': patient}, 'name')


def manage_fee_validity(appointment_name, method, ref_invoice=None):
	appointment_doc = frappe.get_doc('Patient Appointment', appointment_name)
	validity = check_validity_exists(appointment_doc.practitioner, appointment_doc.patient)
	do_not_update = False
	visited = 0
	if validity:
		fee_validity = frappe.get_doc('Fee Validity', validity)
		# Check if the validity is valid
		if fee_validity.valid_till >= appointment_doc.appointment_date:
			if method == 'on_cancel' and appointment_doc.status != 'Closed':
				if ref_invoice == fee_validity.ref_invoice:
					visited = fee_validity.visited - 1
					if visited < 0:
						visited = 0
					frappe.db.set_value('Fee Validity', fee_validity.name, 'visited', visited)
				do_not_update = True
			elif method == 'on_submit' and fee_validity.visited < fee_validity.max_visits:
				visited = fee_validity.visited + 1
				frappe.db.set_value('Fee Validity', fee_validity.name, 'visited', visited)
				do_not_update = True
			else:
				do_not_update = False

		if not do_not_update:
			fee_validity = update_fee_validity(fee_validity, appointment_doc.appointment_date, ref_invoice)
	else:
		fee_validity = create_fee_validity(appointment_doc.practitioner, appointment_doc.patient, appointment_doc.appointment_date, ref_invoice)

	visited = fee_validity.visited
	mark_appointments_as_invoiced(fee_validity, ref_invoice, method, appointment_doc, visited)

	if method == 'on_cancel':
		ref_invoice_in_fee_validity = frappe.db.get_value('Fee Validity', fee_validity.name, 'ref_invoice')
		if ref_invoice_in_fee_validity == ref_invoice:
			frappe.delete_doc('Fee Validity', fee_validity.name)


def mark_appointments_as_invoiced(fee_validity, ref_invoice, method, appointment_doc, visited):
	if method == 'on_cancel':
		invoiced = True
	else:
		invoiced = False

	patient_appointments = appointments_valid_in_fee_validity(appointment_doc, invoiced)
	if patient_appointments and fee_validity:
		visit = visited
		for appointment in patient_appointments:
			if method == 'on_cancel' and appointment.status != 'Closed':
				if ref_invoice == fee_validity.ref_invoice:
					visited -= 1
					if visited < 0:
						visited = 0
					frappe.db.set_value('Fee Validity', fee_validity.name, 'visited', visited)
				frappe.db.set_value('Patient Appointment', appointment.name, 'invoiced', False)
				manage_doc_for_appointment('Patient Encounter', appointment.name, False)
			elif method == 'on_submit' and int(fee_validity.max_visits) > visit:
				if ref_invoice == fee_validity.ref_invoice:
					visited += 1
					frappe.db.set_value('Fee Validity', fee_validity.name, 'visited', visited)
				frappe.db.set_value('Patient Appointment', appointment.name, 'invoiced', True)
				manage_doc_for_appointment('Patient Encounter', appointment.name, True)
			if ref_invoice == fee_validity.ref_invoice:
				visit = visit + 1


def appointments_valid_in_fee_validity(appointment, invoiced):
	valid_days = frappe.db.get_single_value('Healthcare Settings', 'valid_days')
	max_visits = frappe.db.get_single_value('Healthcare Settings', 'max_visits')
	if int(max_visits) < 1:
		max_visits = 1
	valid_days_date = add_days(getdate(appointment.appointment_date), int(valid_days))

	return frappe.get_list('Patient Appointment',{
		'patient': appointment.patient,
		'invoiced': invoiced,
		'appointment_date':('<=', valid_days_date),
		'appointment_date':('>=', getdate(appointment.appointment_date)),
		'practitioner': appointment.practitioner
	}, order_by='appointment_date', limit=int(max_visits)-1)


def manage_doc_for_appointment(dt_from_appointment, appointment, invoiced):
	dn_from_appointment = frappe.db.get_value(
		dt_from_appointment,
		filters={'appointment': appointment}
	)
	if dn_from_appointment:
		frappe.db.set_value(dt_from_appointment, dn_from_appointment, 'invoiced', invoiced)


@frappe.whitelist()
def get_drugs_to_invoice(encounter):
	encounter = frappe.get_doc('Patient Encounter', encounter)
	if encounter:
		patient = frappe.get_doc('Patient', encounter.patient)
		if patient:
			if patient.customer:
				items_to_invoice = []
				for drug_line in encounter.drug_prescription:
					if drug_line.drug_code:
						qty = 1
						if frappe.db.get_value('Item', drug_line.drug_code, 'stock_uom') == 'Nos':
							qty = drug_line.get_quantity()

						description = ''
						if drug_line.dosage and drug_line.period:
							description = _('{0} for {1}').format(drug_line.dosage, drug_line.period)

						items_to_invoice.append({
							'drug_code': drug_line.drug_code,
							'quantity': qty,
							'description': description
						})
				return items_to_invoice
			else:
				validate_customer_created(patient)


@frappe.whitelist()
def get_children(doctype, parent, company, is_root=False):
	parent_fieldname = "parent_" + doctype.lower().replace(" ", "_")
	fields = [
		"name as value",
		"is_group as expandable",
		"lft",
		"rgt"
	]
	# fields = [ "name", "is_group", "lft", "rgt" ]
	filters = [["ifnull(`{0}`,'')".format(parent_fieldname), "=", "" if is_root else parent]]

	if is_root:
		fields += ["service_unit_type"] if doctype == "Healthcare Service Unit" else []
		filters.append(["company", "=", company])

	else:
		fields += ["service_unit_type", "allow_appointments", "inpatient_occupancy", "occupancy_status"] if doctype == "Healthcare Service Unit" else []
		fields += [parent_fieldname + " as parent"]

	hc_service_units = frappe.get_list(doctype, fields=fields, filters=filters)

	if doctype == "Healthcare Service Unit":
		for each in hc_service_units:
			occupancy_msg = ""
			if each["expandable"] == 1:
				occupied = False
				vacant = False
				child_list = frappe.db.sql("""
					select name, occupancy_status from `tabHealthcare Service Unit`
					where inpatient_occupancy = 1 and
					lft > %s and rgt < %s""",
					(each["lft"], each["rgt"]))
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
					occupancy_total = vacant + occupied
					occupancy_msg = str(occupied) + " Occupied out of " + str(occupancy_total)
			each["occupied_out_of_vacant"] = occupancy_msg
	return hc_service_units


@frappe.whitelist()
def get_patient_vitals(patient, from_date=None, to_date=None):
	if not patient: return

	vitals = frappe.db.get_all('Vital Signs', {
			'docstatus': 1,
			'patient': patient
		}, order_by='signs_date, signs_time')

	if len(vitals):
		return vitals
	return False


@frappe.whitelist()
def render_docs_as_html(docs):
	# docs key value pair {doctype: docname}
	docs_html = "<div class='col-md-12 col-sm-12 text-muted'>"
	for doc in docs:
		docs_html += render_doc_as_html(doc['doctype'], doc['docname'])['html'] + '<br/>'
		return {'html': docs_html}


@frappe.whitelist()
def render_doc_as_html(doctype, docname, exclude_fields = []):
	#render document as html, three column layout will break
	doc = frappe.get_doc(doctype, docname)
	meta = frappe.get_meta(doctype)
	doc_html = "<div class='col-md-12 col-sm-12'>"
	section_html = ''
	section_label = ''
	html = ''
	sec_on = False
	col_on = 0
	has_data = False
	for df in meta.fields:
		#on section break append append previous section and html to doc html
		if df.fieldtype == "Section Break":
			if has_data and col_on and sec_on:
				doc_html += section_html + html + "</div>"
			elif has_data and not col_on and sec_on:
				doc_html += "<div class='col-md-12 col-sm-12'\
				><div class='col-md-12 col-sm-12'>" \
				+ section_html + html +"</div></div>"
			while col_on:
				doc_html += "</div>"
				col_on -= 1
			sec_on = True
			has_data= False
			col_on = 0
			section_html = ''
			html = ''
			if df.label:
				section_label = df.label
			continue
		#on column break append html to section html or doc html
		if df.fieldtype == "Column Break":
			if sec_on and has_data:
				section_html += "<div class='col-md-12 col-sm-12'\
				><div class='col-md-6 col\
				-sm-6'><b>" + section_label + "</b>" + html + "</div><div \
				class='col-md-6 col-sm-6'>"
			elif has_data:
				doc_html += "<div class='col-md-12 col-sm-12'><div class='col-m\
				d-6 col-sm-6'>" + html + "</div><div class='col-md-6 col-sm-6'>"
			elif sec_on and not col_on:
				section_html += "<div class='col-md-6 col-sm-6'>"
			html = ''
			col_on += 1
			if df.label:
				html += '<br>' + df.label
			continue
		#on table iterate in items and create table based on in_list_view, append to section html or doc html
		if df.fieldtype == 'Table':
			items = doc.get(df.fieldname)
			if not items: continue
			child_meta = frappe.get_meta(df.options)
			if not has_data : has_data = True
			table_head = ''
			table_row = ''
			create_head = True
			for item in items:
				table_row += '<tr>'
				for cdf in child_meta.fields:
					if cdf.in_list_view:
						if create_head:
							table_head += '<th>' + cdf.label + '</th>'
						if item.get(cdf.fieldname):
							table_row += '<td>' + str(item.get(cdf.fieldname)) \
							+ '</td>'
						else:
							table_row += '<td></td>'
				create_head = False
				table_row += '</tr>'
			if sec_on:
				section_html += "<table class='table table-condensed \
				bordered'>" + table_head +  table_row + '</table>'
			else:
				html += "<table class='table table-condensed table-bordered'>" \
				+ table_head +  table_row + "</table>"
			continue
		#on other field types add label and value to html
		if not df.hidden and not df.print_hide and doc.get(df.fieldname) and df.fieldname not in exclude_fields:
			html +=  '<br>{0} : {1}'.format(df.label or df.fieldname, \
			doc.get(df.fieldname))
			if not has_data : has_data = True
	if sec_on and col_on and has_data:
		doc_html += section_html + html + '</div></div>'
	elif sec_on and not col_on and has_data:
		doc_html += "<div class='col-md-12 col-sm-12'\
		><div class='col-md-12 col-sm-12'>" \
		+ section_html + html +'</div></div>'
	if doc_html:
		doc_html = "<div class='small'><div class='col-md-12 text-right'><a class='btn btn-default btn-xs' href='#Form/%s/%s'></a></div>" %(doctype, docname) + doc_html + '</div>'

	return {'html': doc_html}
