# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe, json
from frappe.utils.make_random import get_random
import datetime
from erpnext.demo.setup.setup_data import import_json
from frappe.utils import getdate
from erpnext.healthcare.doctype.lab_test.lab_test import create_test_from_template

def setup_data():
	frappe.flags.mute_emails = True
	make_masters()
	make_patient()
	make_lab_test()
	make_consulation()
	make_appointment()
	consulation_on_appointment()
	lab_test_on_encounter()
	frappe.db.commit()
	frappe.clear_cache()

def make_masters():
	import_json("Healthcare Practitioner")
	import_drug()
	frappe.db.commit()

def make_patient():
	file_path = get_json_path("Patient")
	with open(file_path, "r") as open_file:
		patient_data = json.loads(open_file.read())
		count = 1

		for d in enumerate(patient_data):
			patient = frappe.new_doc("Patient")
			patient.patient_name = d[1]['patient_name'].title()
			patient.sex = d[1]['gender']
			patient.blood_group = "A Positive"
			patient.date_of_birth = datetime.datetime(1990, 3, 25)
			patient.email_id = d[1]['patient_name'] + "_" + patient.date_of_birth.strftime('%m/%d/%Y') + "@example.com"
			if count <5:
				patient.insert()
				frappe.db.commit()
			count+=1

def make_appointment():
	i = 1
	while i <= 4:
		practitioner = get_random("Healthcare Practitioner")
		department = frappe.get_value("Healthcare Practitioner", practitioner, "department")
		patient = get_random("Patient")
		patient_sex = frappe.get_value("Patient", patient, "sex")
		appointment = frappe.new_doc("Patient Appointment")
		startDate = datetime.datetime.now()
		for x in random_date(startDate,0):
			appointment_datetime = x
		appointment.appointment_datetime = appointment_datetime
		appointment.appointment_time = appointment_datetime
		appointment.appointment_date = appointment_datetime
		appointment.patient = patient
		appointment.patient_sex = patient_sex
		appointment.practitioner = practitioner
		appointment.department = department
		appointment.save(ignore_permissions = True)
		i += 1

def make_consulation():
	for i in range(3):
		practitioner = get_random("Healthcare Practitioner")
		department = frappe.get_value("Healthcare Practitioner", practitioner, "department")
		patient = get_random("Patient")
		patient_sex = frappe.get_value("Patient", patient, "sex")
		encounter = set_encounter(patient, patient_sex, practitioner, department, getdate(), i)
		encounter.save(ignore_permissions=True)

def consulation_on_appointment():
	for i in range(3):
		appointment = get_random("Patient Appointment")
		appointment = frappe.get_doc("Patient Appointment",appointment)
		encounter = set_encounter(appointment.patient, appointment.patient_sex, appointment.practitioner, appointment.department, appointment.appointment_date, i)
		encounter.appointment = appointment.name
		encounter.save(ignore_permissions=True)

def set_encounter(patient, patient_sex, practitioner, department, encounter_date, i):
	encounter = frappe.new_doc("Patient Encounter")
	encounter.patient = patient
	encounter.patient_sex = patient_sex
	encounter.practitioner = practitioner
	encounter.visit_department = department
	encounter.encounter_date = encounter_date
	if i > 2 and patient_sex=='Female':
		encounter.symptoms = "Having chest pains for the last week."
		encounter.diagnosis = """This patient's description of dull, aching,
		exertion related substernal chest pain is suggestive of ischemic
		cardiac origin. Her findings of a FH of early ASCVD, hypertension,
		and early surgical menopause are pertinent risk factors for development
		of coronary artery disease. """
	else:
		encounter = append_drug_rx(encounter)
		encounter = append_test_rx(encounter)
	return encounter

def make_lab_test():
	practitioner = get_random("Healthcare Practitioner")
	patient = get_random("Patient")
	patient_sex = frappe.get_value("Patient", patient, "sex")
	template = get_random("Lab Test Template")
	set_lab_test(patient, patient_sex, practitioner, template)

def lab_test_on_encounter():
	i = 1
	while i <= 2:
		test_rx = get_random("Lab Prescription", filters={'test_created': 0})
		test_rx = frappe.get_doc("Lab Prescription", test_rx)
		encounter = frappe.get_doc("Patient Encounter", test_rx.parent)
		set_lab_test(encounter.patient, encounter.patient_sex, encounter.practitioner, test_rx.test_code, test_rx.name)
		i += 1

def set_lab_test(patient, patient_sex, practitioner, template, rx=None):
	lab_test = frappe.new_doc("Lab Test")
	lab_test.practitioner = practitioner
	lab_test.patient = patient
	lab_test.patient_sex = patient_sex
	lab_test.template = template
	lab_test.prescription = rx
	create_test_from_template(lab_test)

def append_test_rx(encounter):
	i = 1
	while i <= 2:
		test_rx = encounter.append("test_prescription")
		test_rx.test_code = get_random("Lab Test Template")
		i += 1
	return encounter

def append_drug_rx(encounter):
	i = 1
	while i <= 3:
		drug = get_random("Item", filters={"item_group":"Drug"})
		drug = frappe.get_doc("Item", drug)
		drug_rx = encounter.append("drug_prescription")
		drug_rx.drug_code = drug.item_code
		drug_rx.drug_name = drug.item_name
		drug_rx.dosage = get_random("Prescription Dosage")
		drug_rx.period = get_random("Prescription Duration")
		i += 1
	return encounter

def random_date(start,l):
   current = start
   while l >= 0:
      curr = current + datetime.timedelta(minutes=60)
      yield curr
      l-=1

def import_drug():
	frappe.flags.in_import = True
	data = json.loads(open(frappe.get_app_path('erpnext', 'demo', 'data', 'drug_list.json')).read())
	for d in data:
		doc = frappe.new_doc("Item")
		doc.update(d)
		doc.insert()
	frappe.flags.in_import = False

def get_json_path(doctype):
		return frappe.get_app_path('erpnext', 'demo', 'data', frappe.scrub(doctype) + '.json')
