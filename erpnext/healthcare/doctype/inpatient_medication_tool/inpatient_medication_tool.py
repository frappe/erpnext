# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, nowtime, flt
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_account

class InpatientMedicationTool(Document):
	def process_medication_orders(self, orders):
		orders = self.set_available_qty(orders)
		in_stock = check_stock_qty(orders)
		if not in_stock:
			return 'insufficient stock'

		self.make_stock_entry(orders)
		self.update_medication_orders(orders)
		return 'success'

	def set_available_qty(self, orders):
		for d in orders:
			d['available_qty'] = get_stock_qty(d.get('drug'), self.warehouse)

		return orders

	def make_material_receipt(self, orders):
		stock_entry = frappe.new_doc('Stock Entry')
		stock_entry.stock_entry_type = 'Material Receipt'
		stock_entry.to_warehouse = self.warehouse
		stock_entry.company = self.company
		cost_center = frappe.get_cached_value('Company',  self.company,  'cost_center')
		expense_account = get_account(None, 'expense_account', 'Healthcare Settings', self.company)

		for item in orders:
			if flt(item.get('available_qty')) < flt(item.get('dosage')):
				se_child = stock_entry.append('items')
				se_child.item_code = item.get('drug')
				se_child.item_name = item.get('drug_name')
				se_child.uom = frappe.db.get_value('Item', item.get('drug'), 'stock_uom')
				se_child.stock_uom = se_child.uom
				se_child.qty = flt(flt(item.get('dosage')) - flt(item.get('available_qty')))
				se_child.t_warehouse = self.warehouse
				# in stock uom
				se_child.conversion_factor = 1
				se_child.cost_center = cost_center
				se_child.expense_account = expense_account

		stock_entry.submit()
		return stock_entry.name

	def make_stock_entry(self, orders):
		stock_entry = frappe.new_doc('Stock Entry')
		stock_entry.stock_entry_type = 'Material Issue'
		stock_entry.from_warehouse = self.warehouse
		stock_entry.company = self.company
		cost_center = frappe.get_cached_value('Company',  self.company,  'cost_center')
		expense_account = get_account(None, 'expense_account', 'Healthcare Settings', self.company)

		for item in orders:
			se_child = stock_entry.append('items')
			se_child.item_code = item.get('drug')
			se_child.item_name = item.get('drug_name')
			se_child.uom = frappe.db.get_value('Item', item.get('drug'), 'stock_uom')
			se_child.stock_uom = se_child.uom
			se_child.qty = flt(item.get('dosage'))
			# in stock uom
			se_child.conversion_factor = 1
			se_child.cost_center = cost_center
			se_child.expense_account = expense_account

		stock_entry.submit()
		return stock_entry.name

	def update_medication_orders(self, orders):
		completed_orders = []
		for entry in orders:
			completed_orders.append(entry.get('name'))

		frappe.db.sql("""
			UPDATE `tabInpatient Medication Order Entry`
			SET is_completed = 1
			WHERE name IN %(orders)s
		""", {'orders': completed_orders})


@frappe.whitelist()
def get_medication_orders(date, is_completed=0):
	data = frappe.db.sql("""
		SELECT
			ip.inpatient_record, ip.patient, ip.patient_name,
			entry.name, entry.drug, entry.drug_name, entry.dosage, entry.dosage_form, entry.time
		FROM
			`tabInpatient Medication Order` ip
		INNER JOIN
			`tabInpatient Medication Order Entry` entry
		ON
			ip.name = entry.parent
		WHERE
			entry.date = %(date)s and
			entry.is_completed = %(is_completed)s
		ORDER BY
			entry.time
	""", {'date': date, 'is_completed': is_completed}, as_dict=1)

	for entry in data:
		inpatient_record = entry.inpatient_record
		entry['service_unit'] = get_current_healthcare_service_unit(inpatient_record)

		if entry['patient'] != entry['patient_name']:
			entry['patient'] = entry['patient'] + ' - ' + entry['patient_name']

	return data

def get_current_healthcare_service_unit(inpatient_record):
	ip_record = frappe.get_doc('Inpatient Record', inpatient_record)
	return ip_record.inpatient_occupancies[-1].service_unit

def check_stock_qty(orders):
	allow_negative_stock = frappe.db.get_single_value('Stock Settings', 'allow_negative_stock')

	in_stock = True
	for d in orders:
		# validate qty
		if not allow_negative_stock and flt(d.get('available_qty')) < flt(d.get('dosage')):
			in_stock = False
			break

	return in_stock

def get_stock_qty(item_code, warehouse):
	return get_previous_sle({
		'item_code': item_code,
		'warehouse': warehouse,
		'posting_date': nowdate(),
		'posting_time': nowtime()
	}).get('qty_after_transaction') or 0
