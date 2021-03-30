# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
import datetime
from frappe.utils import getdate, now_datetime
from erpnext.healthcare.doctype.inpatient_record.test_inpatient_record import create_patient, create_inpatient, get_healthcare_service_unit, mark_invoiced_inpatient_occupancy
from erpnext.healthcare.doctype.inpatient_record.inpatient_record import admit_patient, discharge_patient, schedule_discharge
from erpnext.healthcare.doctype.inpatient_medication_order.test_inpatient_medication_order import create_ipmo, create_ipme
from erpnext.healthcare.report.inpatient_medication_orders.inpatient_medication_orders import execute

class TestInpatientMedicationOrders(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		frappe.db.sql("delete from `tabInpatient Medication Order` where company='_Test Company'")
		frappe.db.sql("delete from `tabInpatient Medication Entry` where company='_Test Company'")
		self.patient = create_patient()
		self.ip_record = create_records(self.patient)

	def test_inpatient_medication_orders_report(self):
		filters = {
			'company': '_Test Company',
			'from_date': getdate(),
			'to_date': getdate(),
			'patient': '_Test IPD Patient',
			'service_unit': 'Test Service Unit Ip Occupancy - _TC'
		}

		report = execute(filters)

		expected_data = [
			{
				'patient': '_Test IPD Patient',
				'inpatient_record': self.ip_record.name,
				'practitioner': None,
				'drug': 'Dextromethorphan',
				'drug_name': 'Dextromethorphan',
				'dosage': 1.0,
				'dosage_form': 'Tablet',
				'date': getdate(),
				'time': datetime.timedelta(seconds=32400),
				'is_completed': 0,
				'healthcare_service_unit': 'Test Service Unit Ip Occupancy - _TC'
			},
			{
				'patient': '_Test IPD Patient',
				'inpatient_record': self.ip_record.name,
				'practitioner': None,
				'drug': 'Dextromethorphan',
				'drug_name': 'Dextromethorphan',
				'dosage': 1.0,
				'dosage_form': 'Tablet',
				'date': getdate(),
				'time': datetime.timedelta(seconds=50400),
				'is_completed': 0,
				'healthcare_service_unit': 'Test Service Unit Ip Occupancy - _TC'
			},
			{
				'patient': '_Test IPD Patient',
				'inpatient_record': self.ip_record.name,
				'practitioner': None,
				'drug': 'Dextromethorphan',
				'drug_name': 'Dextromethorphan',
				'dosage': 1.0,
				'dosage_form': 'Tablet',
				'date': getdate(),
				'time': datetime.timedelta(seconds=75600),
				'is_completed': 0,
				'healthcare_service_unit': 'Test Service Unit Ip Occupancy - _TC'
			}
		]

		self.assertEqual(expected_data, report[1])

		filters = frappe._dict(from_date=getdate(), to_date=getdate(), from_time='', to_time='')
		ipme = create_ipme(filters)
		ipme.submit()

		filters = {
			'company': '_Test Company',
			'from_date': getdate(),
			'to_date': getdate(),
			'patient': '_Test IPD Patient',
			'service_unit': 'Test Service Unit Ip Occupancy - _TC',
			'show_completed_orders': 0
		}

		report = execute(filters)
		self.assertEqual(len(report[1]), 0)

	def tearDown(self):
		if frappe.db.get_value('Patient', self.patient, 'inpatient_record'):
			# cleanup - Discharge
			schedule_discharge(frappe.as_json({'patient': self.patient}))
			self.ip_record.reload()
			mark_invoiced_inpatient_occupancy(self.ip_record)

			self.ip_record.reload()
			discharge_patient(self.ip_record)

		for entry in frappe.get_all('Inpatient Medication Entry'):
			doc = frappe.get_doc('Inpatient Medication Entry', entry.name)
			doc.cancel()
			doc.delete()

		for entry in frappe.get_all('Inpatient Medication Order'):
			doc = frappe.get_doc('Inpatient Medication Order', entry.name)
			doc.cancel()
			doc.delete()


def create_records(patient):
	frappe.db.sql("""delete from `tabInpatient Record`""")

	# Admit
	ip_record = create_inpatient(patient)
	ip_record.expected_length_of_stay = 0
	ip_record.save()
	ip_record.reload()
	service_unit = get_healthcare_service_unit('Test Service Unit Ip Occupancy')
	admit_patient(ip_record, service_unit, now_datetime())

	ipmo = create_ipmo(patient)
	ipmo.submit()

	return ip_record
