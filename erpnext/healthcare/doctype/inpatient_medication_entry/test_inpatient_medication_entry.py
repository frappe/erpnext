# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import add_days, getdate, now_datetime
from erpnext.healthcare.doctype.inpatient_record.test_inpatient_record import create_patient, create_inpatient, get_healthcare_service_unit, mark_invoiced_inpatient_occupancy
from erpnext.healthcare.doctype.inpatient_record.inpatient_record import admit_patient, discharge_patient, schedule_discharge
from erpnext.healthcare.doctype.inpatient_medication_order.test_inpatient_medication_order import create_ipmo, create_ipme
from erpnext.healthcare.doctype.inpatient_medication_entry.inpatient_medication_entry import get_drug_shortage_map, make_difference_stock_entry
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_account

class TestInpatientMedicationEntry(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabInpatient Record`""")
		frappe.db.sql("""delete from `tabInpatient Medication Order`""")
		frappe.db.sql("""delete from `tabInpatient Medication Entry`""")
		self.patient = create_patient()

		# Admit
		ip_record = create_inpatient(self.patient)
		ip_record.expected_length_of_stay = 0
		ip_record.save()
		ip_record.reload()
		service_unit = get_healthcare_service_unit()
		admit_patient(ip_record, service_unit, now_datetime())
		self.ip_record = ip_record

	def test_filters_for_fetching_pending_mo(self):
		ipmo = create_ipmo(self.patient)
		ipmo.submit()
		ipmo.reload()

		date = add_days(getdate(), -1)
		filters = frappe._dict(
			from_date=date,
			to_date=date,
			from_time='',
			to_time='',
			item_code='Dextromethorphan',
			patient=self.patient
		)

		ipme = create_ipme(filters, update_stock=0)

		# 3 dosages per day
		self.assertEqual(len(ipme.medication_orders), 3)
		self.assertEqual(getdate(ipme.medication_orders[0].datetime), date)

	def test_ipme_with_stock_update(self):
		ipmo = create_ipmo(self.patient)
		ipmo.submit()
		ipmo.reload()

		date = add_days(getdate(), -1)
		filters = frappe._dict(
			from_date=date,
			to_date=date,
			from_time='',
			to_time='',
			item_code='Dextromethorphan',
			patient=self.patient
		)

		make_stock_entry()
		ipme = create_ipme(filters, update_stock=1)
		ipme.submit()
		ipme.reload()

		# test order completed
		is_order_completed = frappe.db.get_value('Inpatient Medication Order Entry',
			ipme.medication_orders[0].against_imoe, 'is_completed')
		self.assertEqual(is_order_completed, 1)

		# test stock entry
		stock_entry = frappe.db.exists('Stock Entry', {'inpatient_medication_entry': ipme.name})
		self.assertTrue(stock_entry)

		# check references
		stock_entry = frappe.get_doc('Stock Entry', stock_entry)
		self.assertEqual(stock_entry.items[0].patient, self.patient)
		self.assertEqual(stock_entry.items[0].inpatient_medication_entry_child, ipme.medication_orders[0].name)

	def test_drug_shortage_stock_entry(self):
		ipmo = create_ipmo(self.patient)
		ipmo.submit()
		ipmo.reload()

		date = add_days(getdate(), -1)
		filters = frappe._dict(
			from_date=date,
			to_date=date,
			from_time='',
			to_time='',
			item_code='Dextromethorphan',
			patient=self.patient
		)

		# check drug shortage
		ipme = create_ipme(filters, update_stock=1)
		ipme.warehouse = 'Finished Goods - _TC'
		ipme.save()
		drug_shortage = get_drug_shortage_map(ipme.medication_orders, ipme.warehouse)
		self.assertEqual(drug_shortage.get('Dextromethorphan'), 3)

		# check material transfer for drug shortage
		make_stock_entry()
		stock_entry = make_difference_stock_entry(ipme.name)
		self.assertEqual(stock_entry.items[0].item_code, 'Dextromethorphan')
		self.assertEqual(stock_entry.items[0].qty, 3)
		stock_entry.from_warehouse = 'Stores - _TC'
		stock_entry.submit()

		ipme.reload()
		ipme.submit()

	def tearDown(self):
		# cleanup - Discharge
		schedule_discharge(frappe.as_json({'patient': self.patient}))
		self.ip_record.reload()
		mark_invoiced_inpatient_occupancy(self.ip_record)

		self.ip_record.reload()
		discharge_patient(self.ip_record)

		for entry in frappe.get_all('Inpatient Medication Entry'):
			doc = frappe.get_doc('Inpatient Medication Entry', entry.name)
			doc.cancel()

		for entry in frappe.get_all('Inpatient Medication Order'):
			doc = frappe.get_doc('Inpatient Medication Order', entry.name)
			doc.cancel()

def make_stock_entry(warehouse=None):
	frappe.db.set_value('Company', '_Test Company', {
		'stock_adjustment_account': 'Stock Adjustment - _TC',
		'default_inventory_account': 'Stock In Hand - _TC'
	})
	stock_entry = frappe.new_doc('Stock Entry')
	stock_entry.stock_entry_type = 'Material Receipt'
	stock_entry.company = '_Test Company'
	stock_entry.to_warehouse = warehouse or 'Stores - _TC'
	expense_account = get_account(None, 'expense_account', 'Healthcare Settings', '_Test Company')
	se_child = stock_entry.append('items')
	se_child.item_code = 'Dextromethorphan'
	se_child.item_name = 'Dextromethorphan'
	se_child.uom = 'Nos'
	se_child.stock_uom = 'Nos'
	se_child.qty = 6
	se_child.t_warehouse = 'Stores - _TC'
	# in stock uom
	se_child.conversion_factor = 1.0
	se_child.expense_account = expense_account
	stock_entry.submit()