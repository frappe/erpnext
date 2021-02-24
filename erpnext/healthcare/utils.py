# -*- coding: utf-8 -*-
# Copyright (c) 2018, earthians and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import math
import frappe
import json
from frappe import _
from frappe.utils.formatters import format_value
from frappe.utils import time_diff_in_hours, rounded
from six import string_types
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_income_account
from erpnext.healthcare.doctype.fee_validity.fee_validity import create_fee_validity
from erpnext.healthcare.doctype.lab_test.lab_test import create_multiple

@frappe.whitelist()
def get_healthcare_services_to_invoice(patient, company):
	patient = frappe.get_doc('Patient', patient)
	items_to_invoice = []
	if patient:
		validate_customer_created(patient)
		# Customer validated, build a list of billable services
		items_to_invoice += get_appointments_to_invoice(patient, company)
		items_to_invoice += get_encounters_to_invoice(patient, company)
		items_to_invoice += get_lab_tests_to_invoice(patient, company)
		items_to_invoice += get_clinical_procedures_to_invoice(patient, company)
		items_to_invoice += get_inpatient_services_to_invoice(patient, company)
		items_to_invoice += get_therapy_plans_to_invoice(patient, company)
		items_to_invoice += get_therapy_sessions_to_invoice(patient, company)

		return items_to_invoice


def validate_customer_created(patient):
	if not frappe.db.get_value('Patient', patient.name, 'customer'):
		msg = _("Please set a Customer linked to the Patient")
		msg +=  " <b><a href='#Form/Patient/{0}'>{0}</a></b>".format(patient.name)
		frappe.throw(msg, title=_('Customer Not Found'))


def get_appointments_to_invoice(patient, company):
	appointments_to_invoice = []
	patient_appointments = frappe.get_list(
			'Patient Appointment',
			fields = '*',
			filters = {'patient': patient.name, 'company': company, 'invoiced': 0, 'status': ['not in', 'Cancelled']},
			order_by = 'appointment_date'
		)

	for appointment in patient_appointments:
		# Procedure Appointments
		if appointment.procedure_template:
			if frappe.db.get_value('Clinical Procedure Template', appointment.procedure_template, 'is_billable'):
				appointments_to_invoice.append({
					'reference_type': 'Patient Appointment',
					'reference_name': appointment.name,
					'service': appointment.procedure_template
				})
		# Consultation Appointments, should check fee validity
		else:
			if frappe.db.get_single_value('Healthcare Settings', 'enable_free_follow_ups') and \
				frappe.db.exists('Fee Validity Reference', {'appointment': appointment.name}):
					continue # Skip invoicing, fee validty present
			practitioner_charge = 0
			income_account = None
			service_item = None
			if appointment.practitioner:
				details = get_service_item_and_practitioner_charge(appointment)
				service_item = details.get('service_item')
				practitioner_charge = details.get('practitioner_charge')
				income_account = get_income_account(appointment.practitioner, appointment.company)
			appointments_to_invoice.append({
				'reference_type': 'Patient Appointment',
				'reference_name': appointment.name,
				'service': service_item,
				'rate': practitioner_charge,
				'income_account': income_account
			})

	return appointments_to_invoice


def get_encounters_to_invoice(patient, company):
	if not isinstance(patient, str):
		patient = patient.name
	encounters_to_invoice = []
	encounters = frappe.get_list(
		'Patient Encounter',
		fields=['*'],
		filters={'patient': patient, 'company': company, 'invoiced': False, 'docstatus': 1}
	)
	if encounters:
		for encounter in encounters:
			if not encounter.appointment:
				practitioner_charge = 0
				income_account = None
				service_item = None
				if encounter.practitioner:
					if encounter.inpatient_record and \
						frappe.db.get_single_value('Healthcare Settings', 'do_not_bill_inpatient_encounters'):
						continue

					details = get_service_item_and_practitioner_charge(encounter)
					service_item = details.get('service_item')
					practitioner_charge = details.get('practitioner_charge')
					income_account = get_income_account(encounter.practitioner, encounter.company)

				encounters_to_invoice.append({
					'reference_type': 'Patient Encounter',
					'reference_name': encounter.name,
					'service': service_item,
					'rate': practitioner_charge,
					'income_account': income_account
				})

	return encounters_to_invoice


def get_lab_tests_to_invoice(patient, company):
	lab_tests_to_invoice = []
	lab_tests = frappe.get_list(
		'Lab Test',
		fields=['name', 'template'],
		filters={'patient': patient.name, 'company': company, 'invoiced': False, 'docstatus': 1}
	)
	for lab_test in lab_tests:
		item, is_billable = frappe.get_cached_value('Lab Test Template', lab_test.template, ['item', 'is_billable'])
		if is_billable:
			lab_tests_to_invoice.append({
				'reference_type': 'Lab Test',
				'reference_name': lab_test.name,
				'service': item
			})

	lab_prescriptions = frappe.db.sql(
		'''
			SELECT
				lp.name, lp.lab_test_code
			FROM
				`tabPatient Encounter` et, `tabLab Prescription` lp
			WHERE
				et.patient=%s
				and lp.parent=et.name
				and lp.lab_test_created=0
				and lp.invoiced=0
		''', (patient.name), as_dict=1)

	for prescription in lab_prescriptions:
		item, is_billable = frappe.get_cached_value('Lab Test Template', prescription.lab_test_code, ['item', 'is_billable'])
		if prescription.lab_test_code and is_billable:
			lab_tests_to_invoice.append({
				'reference_type': 'Lab Prescription',
				'reference_name': prescription.name,
				'service': item
			})

	return lab_tests_to_invoice


def get_clinical_procedures_to_invoice(patient, company):
	clinical_procedures_to_invoice = []
	procedures = frappe.get_list(
		'Clinical Procedure',
		fields='*',
		filters={'patient': patient.name, 'company': company, 'invoiced': False}
	)
	for procedure in procedures:
		if not procedure.appointment:
			item, is_billable = frappe.get_cached_value('Clinical Procedure Template', procedure.procedure_template, ['item', 'is_billable'])
			if procedure.procedure_template and is_billable:
				clinical_procedures_to_invoice.append({
					'reference_type': 'Clinical Procedure',
					'reference_name': procedure.name,
					'service': item
				})

		# consumables
		if procedure.invoice_separately_as_consumables and procedure.consume_stock \
			and procedure.status == 'Completed' and not procedure.consumption_invoiced:

			service_item = frappe.db.get_single_value('Healthcare Settings', 'clinical_procedure_consumable_item')
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

	procedure_prescriptions = frappe.db.sql(
		'''
			SELECT
				pp.name, pp.procedure
			FROM
				`tabPatient Encounter` et, `tabProcedure Prescription` pp
			WHERE
				et.patient=%s
				and pp.parent=et.name
				and pp.procedure_created=0
				and pp.invoiced=0
				and pp.appointment_booked=0
		''', (patient.name), as_dict=1)

	for prescription in procedure_prescriptions:
		item, is_billable = frappe.get_cached_value('Clinical Procedure Template', prescription.procedure, ['item', 'is_billable'])
		if is_billable:
			clinical_procedures_to_invoice.append({
				'reference_type': 'Procedure Prescription',
				'reference_name': prescription.name,
				'service': item
			})

	return clinical_procedures_to_invoice


def get_inpatient_services_to_invoice(patient, company):
	services_to_invoice = []
	inpatient_services = frappe.db.sql(
		'''
			SELECT
				io.*
			FROM
				`tabInpatient Record` ip, `tabInpatient Occupancy` io
			WHERE
				ip.patient=%s
				and ip.company=%s
				and io.parent=ip.name
				and io.left=1
				and io.invoiced=0
		''', (patient.name, company), as_dict=1)

	for inpatient_occupancy in inpatient_services:
		service_unit_type = frappe.db.get_value('Healthcare Service Unit', inpatient_occupancy.service_unit, 'service_unit_type')
		service_unit_type = frappe.get_cached_doc('Healthcare Service Unit Type', service_unit_type)
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


def get_therapy_plans_to_invoice(patient, company):
	therapy_plans_to_invoice = []
	therapy_plans = frappe.get_list(
		'Therapy Plan',
		fields=['therapy_plan_template', 'name'],
		filters={
			'patient': patient.name,
			'invoiced': 0,
			'company': company,
			'therapy_plan_template': ('!=', '')
		}
	)
	for plan in therapy_plans:
		therapy_plans_to_invoice.append({
			'reference_type': 'Therapy Plan',
			'reference_name': plan.name,
			'service': frappe.db.get_value('Therapy Plan Template', plan.therapy_plan_template, 'linked_item')
		})

	return therapy_plans_to_invoice


def get_therapy_sessions_to_invoice(patient, company):
	therapy_sessions_to_invoice = []
	therapy_plans = frappe.db.get_all('Therapy Plan', {'therapy_plan_template': ('!=', '')})
	therapy_plans_created_from_template = []
	for entry in therapy_plans:
		therapy_plans_created_from_template.append(entry.name)

	therapy_sessions = frappe.get_list(
		'Therapy Session',
		fields='*',
		filters={
			'patient': patient.name,
			'invoiced': 0,
			'company': company,
			'therapy_plan': ('not in', therapy_plans_created_from_template)
		}
	)
	for therapy in therapy_sessions:
		if not therapy.appointment:
			if therapy.therapy_type and frappe.db.get_value('Therapy Type', therapy.therapy_type, 'is_billable'):
				therapy_sessions_to_invoice.append({
					'reference_type': 'Therapy Session',
					'reference_name': therapy.name,
					'service': frappe.db.get_value('Therapy Type', therapy.therapy_type, 'item')
				})

	return therapy_sessions_to_invoice

@frappe.whitelist()
def get_service_item_and_practitioner_charge(doc):
	if isinstance(doc, string_types):
		doc = json.loads(doc)
		doc = frappe.get_doc(doc)

	service_item = None
	practitioner_charge = None
	department = doc.medical_department if doc.doctype == 'Patient Encounter' else doc.department

	is_inpatient = doc.inpatient_record

	if doc.get('appointment_type'):
		service_item, practitioner_charge = get_appointment_type_service_item(doc.appointment_type, department, is_inpatient)

	if not service_item and not practitioner_charge:
		service_item, practitioner_charge = get_practitioner_service_item(doc.practitioner, is_inpatient)
		if not service_item:
			service_item = get_healthcare_service_item(is_inpatient)

	if not service_item:
		throw_config_service_item(is_inpatient)

	if not practitioner_charge:
		throw_config_practitioner_charge(is_inpatient, doc.practitioner)

	return {'service_item': service_item, 'practitioner_charge': practitioner_charge}


def get_appointment_type_service_item(appointment_type, department, is_inpatient):
	from erpnext.healthcare.doctype.appointment_type.appointment_type import get_service_item_based_on_department

	item_list = get_service_item_based_on_department(appointment_type, department)
	service_item = None
	practitioner_charge = None

	if item_list:
		if is_inpatient:
			service_item = item_list.get('inpatient_visit_charge_item')
			practitioner_charge = item_list.get('inpatient_visit_charge')
		else:
			service_item = item_list.get('op_consulting_charge_item')
			practitioner_charge = item_list.get('op_consulting_charge')

	return service_item, practitioner_charge


def throw_config_service_item(is_inpatient):
	service_item_label = _('Out Patient Consulting Charge Item')
	if is_inpatient:
		service_item_label = _('Inpatient Visit Charge Item')

	msg = _(('Please Configure {0} in ').format(service_item_label) \
		+ '''<b><a href='#Form/Healthcare Settings'>Healthcare Settings</a></b>''')
	frappe.throw(msg, title=_('Missing Configuration'))


def throw_config_practitioner_charge(is_inpatient, practitioner):
	charge_name = _('OP Consulting Charge')
	if is_inpatient:
		charge_name = _('Inpatient Visit Charge')

	msg = _(('Please Configure {0} for Healthcare Practitioner').format(charge_name) \
		+ ''' <b><a href='#Form/Healthcare Practitioner/{0}'>{0}</a></b>'''.format(practitioner))
	frappe.throw(msg, title=_('Missing Configuration'))


def get_practitioner_service_item(practitioner, is_inpatient):
	service_item = None
	practitioner_charge = None

	if is_inpatient:
		service_item, practitioner_charge = frappe.db.get_value('Healthcare Practitioner', practitioner, ['inpatient_visit_charge_item', 'inpatient_visit_charge'])
	else:
		service_item, practitioner_charge = frappe.db.get_value('Healthcare Practitioner', practitioner, ['op_consulting_charge_item', 'op_consulting_charge'])

	return service_item, practitioner_charge


def get_healthcare_service_item(is_inpatient):
	service_item = None

	if is_inpatient:
		service_item = frappe.db.get_single_value('Healthcare Settings', 'inpatient_visit_charge_item')
	else:
		service_item = frappe.db.get_single_value('Healthcare Settings', 'op_consulting_charge_item')

	return service_item


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
		service_item = frappe.db.get_single_value('Healthcare Settings', 'clinical_procedure_consumable_item')
		if service_item == item.item_code:
			frappe.db.set_value(item.reference_dt, item.reference_dn, 'consumption_invoiced', invoiced)
		else:
			frappe.db.set_value(item.reference_dt, item.reference_dn, 'invoiced', invoiced)
	else:
		frappe.db.set_value(item.reference_dt, item.reference_dn, 'invoiced', invoiced)

	if item.reference_dt == 'Patient Appointment':
		if frappe.db.get_value('Patient Appointment', item.reference_dn, 'procedure_template'):
			dt_from_appointment = 'Clinical Procedure'
		else:
			dt_from_appointment = 'Patient Encounter'
		manage_doc_for_appointment(dt_from_appointment, item.reference_dn, invoiced)

	elif item.reference_dt == 'Lab Prescription':
		manage_prescriptions(invoiced, item.reference_dt, item.reference_dn, 'Lab Test', 'lab_test_created')

	elif item.reference_dt == 'Procedure Prescription':
		manage_prescriptions(invoiced, item.reference_dt, item.reference_dn, 'Clinical Procedure', 'procedure_created')


def validate_invoiced_on_submit(item):
	if item.reference_dt == 'Clinical Procedure' and \
		frappe.db.get_single_value('Healthcare Settings', 'clinical_procedure_consumable_item') == item.item_code:
		is_invoiced = frappe.db.get_value(item.reference_dt, item.reference_dn, 'consumption_invoiced')
	else:
		is_invoiced = frappe.db.get_value(item.reference_dt, item.reference_dn, 'invoiced')
	if is_invoiced:
		frappe.throw(_('The item referenced by {0} - {1} is already invoiced').format(
			item.reference_dt, item.reference_dn))


def manage_prescriptions(invoiced, ref_dt, ref_dn, dt, created_check_field):
	created = frappe.db.get_value(ref_dt, ref_dn, created_check_field)
	if created:
		# Fetch the doc created for the prescription
		doc_created = frappe.db.get_value(dt, {'prescription': ref_dn})
		frappe.db.set_value(dt, doc_created, 'invoiced', invoiced)


def check_fee_validity(appointment):
	if not frappe.db.get_single_value('Healthcare Settings', 'enable_free_follow_ups'):
		return

	validity = frappe.db.exists('Fee Validity', {
		'practitioner': appointment.practitioner,
		'patient': appointment.patient,
		'valid_till': ('>=', appointment.appointment_date)
	})
	if not validity:
		return

	validity = frappe.get_doc('Fee Validity', validity)
	return validity


def manage_fee_validity(appointment):
	fee_validity = check_fee_validity(appointment)

	if fee_validity:
		if appointment.status == 'Cancelled' and fee_validity.visited > 0:
			fee_validity.visited -= 1
			frappe.db.delete('Fee Validity Reference', {'appointment': appointment.name})
		elif fee_validity.status == 'Completed':
			return
		else:
			fee_validity.visited += 1
			fee_validity.append('ref_appointments', {
				'appointment': appointment.name
			})
		fee_validity.save(ignore_permissions=True)
	else:
		fee_validity = create_fee_validity(appointment)
	return fee_validity


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
				child_list = frappe.db.sql(
					'''
						SELECT
							name, occupancy_status
						FROM
							`tabHealthcare Service Unit`
						WHERE
							inpatient_occupancy = 1
							and lft > %s and rgt < %s
					''', (each['lft'], each['rgt']))

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

	vitals = frappe.db.get_all('Vital Signs', filters={
			'docstatus': 1,
			'patient': patient
		}, order_by='signs_date, signs_time', fields=['*'])

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
			if doc.get(df.fieldname):
				formatted_value = format_value(doc.get(df.fieldname), meta.get_field(df.fieldname), doc)
				html +=  '<br>{0} : {1}'.format(df.label or df.fieldname, formatted_value)

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
