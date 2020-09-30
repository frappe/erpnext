# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form
from erpnext.stock.utils import get_latest_stock_qty
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_account

class InpatientMedicationEntry(Document):
	def validate(self):
		self.validate_medication_orders()

	def get_medication_orders(self):
		# pull inpatient medication orders based on selected filters
		orders = get_pending_medication_orders(self)

		if orders:
			self.add_mo_to_table(orders)
		else:
			self.set('medication_orders', [])
			frappe.msgprint(_('No pending medication orders found for selected criteria'))

	def add_mo_to_table(self, orders):
		# Add medication orders in the child table
		self.set('medication_orders', [])

		for data in orders:
			self.append('medication_orders', {
				'patient': data.patient,
				'patient_name': data.patient_name,
				'inpatient_record': data.inpatient_record,
				'service_unit': data.service_unit,
				'datetime': "%s %s" % (data.date, data.time or "00:00:00"),
				'drug_code': data.drug,
				'drug_name': data.drug_name,
				'dosage': data.dosage,
				'dosage_form': data.dosage_form,
				'against_imo': data.parent,
				'against_imoe': data.name
			})

	def on_submit(self):
		self.validate_medication_orders()
		success_msg = ""
		if self.update_stock:
			stock_entry = self.process_stock()
			success_msg += _('Stock Entry {0} created and ').format(
				frappe.bold(get_link_to_form('Stock Entry', stock_entry)))

		self.update_medication_orders()
		success_msg += _('Inpatient Medication Orders updated successfully')
		frappe.msgprint(success_msg, title=_('Success'), indicator='green')

	def validate_medication_orders(self):
		for entry in self.medication_orders:
			docstatus, is_completed = frappe.db.get_value('Inpatient Medication Order Entry', entry.against_imoe,
				['docstatus', 'is_completed'])

			if docstatus == 2:
				frappe.throw(_('Row {0}: Cannot create Inpatient Medication Entry against cancelled Inpatient Medication Order {1}').format(
					entry.idx, get_link_to_form(entry.against_imo)))

			if is_completed:
				frappe.throw(_('Row {0}: This Medication Order is already marked as completed').format(
					entry.idx))

	def on_cancel(self):
		self.update_medication_orders(on_cancel=True)

	def process_stock(self):
		allow_negative_stock = frappe.db.get_single_value('Stock Settings', 'allow_negative_stock')
		if not allow_negative_stock:
			self.check_stock_qty()

		return self.make_stock_entry()

	def update_medication_orders(self, on_cancel=False):
		# for marking order completion status
		orders = []
		# orders mapped
		order_entry_map = dict()

		for entry in self.medication_orders:
			orders.append(entry.against_imoe)
			parent = entry.against_imo
			if not order_entry_map.get(parent):
				order_entry_map[parent] = 0

			order_entry_map[parent] += 1

		# mark completion status
		is_completed = 1
		if on_cancel:
			is_completed = 0

		frappe.db.sql("""
			UPDATE `tabInpatient Medication Order Entry`
			SET is_completed = %(is_completed)s
			WHERE name IN %(orders)s
		""", {'orders': orders, 'is_completed': is_completed})

		# update status and completed orders count
		for order, count in order_entry_map.items():
			medication_order = frappe.get_doc('Inpatient Medication Order', order)
			completed_orders = flt(count)
			current_value = frappe.db.get_value('Inpatient Medication Order', order, 'completed_orders')

			if on_cancel:
				completed_orders = flt(current_value) - flt(count)
			else:
				completed_orders = flt(current_value) + flt(count)

			medication_order.db_set('completed_orders', completed_orders)
			medication_order.set_status()

	def check_stock_qty(self):
		from erpnext.stock.stock_ledger import NegativeStockError

		drug_availability = dict()
		for d in self.medication_orders:
			if not drug_availability.get(d.drug_code):
				drug_availability[d.drug_code] = 0
			drug_availability[d.drug_code] += flt(d.dosage)

		for drug, dosage in drug_availability.items():
			available_qty = get_latest_stock_qty(drug, self.warehouse)

			# validate qty
			if flt(available_qty) < flt(dosage):
				frappe.throw(_('Quantity not available for {0} in warehouse {1}').format(
					frappe.bold(drug), frappe.bold(self.warehouse))
					+ '<br><br>' + _('Available quantity is {0}, you need {1}').format(
					frappe.bold(available_qty), frappe.bold(dosage))
					+ '<br><br>' + _('Please enable Allow Negative Stock in Stock Settings or create Stock Entry to proceed.'),
					NegativeStockError, title=_('Insufficient Stock'))

	def make_stock_entry(self):
		stock_entry = frappe.new_doc('Stock Entry')
		stock_entry.stock_entry_type = 'Material Issue'
		stock_entry.from_warehouse = self.warehouse
		stock_entry.company = self.company
		stock_entry.inpatient_medication_entry = self.name
		cost_center = frappe.get_cached_value('Company',  self.company,  'cost_center')
		expense_account = get_account(None, 'expense_account', 'Healthcare Settings', self.company)

		for entry in self.medication_orders:
			se_child = stock_entry.append('items')
			se_child.item_code = entry.drug_code
			se_child.item_name = entry.drug_name
			se_child.uom = frappe.db.get_value('Item', entry.drug_code, 'stock_uom')
			se_child.stock_uom = se_child.uom
			se_child.qty = flt(entry.dosage)
			# in stock uom
			se_child.conversion_factor = 1
			se_child.cost_center = cost_center
			se_child.expense_account = expense_account
			# references
			se_child.patient = entry.patient
			se_child.inpatient_medication_entry_child = entry.name

		stock_entry.submit()
		return stock_entry.name


def get_pending_medication_orders(entry):
	parent_filter = child_filter = ''
	values = dict(company=entry.company)

	if entry.from_date:
		child_filter += ' and entry.date >= %(from_date)s'
		values['from_date'] = entry.from_date

	if entry.to_date:
		child_filter += ' and entry.date <= %(to_date)s'
		values['to_date'] = entry.to_date

	if entry.from_time:
		child_filter += ' and entry.time >= %(from_time)s'
		values['from_time'] = entry.from_time

	if entry.to_time:
		child_filter += ' and entry.time <= %(to_time)s'
		values['to_time'] = entry.to_time

	if entry.patient:
		parent_filter += ' and ip.patient = %(patient)s'
		values['patient'] = frappe.db.escape(entry.patient)

	if entry.practitioner:
		parent_filter += ' and ip.practitioner = %(practitioner)s'
		values['practitioner'] = frappe.db.escape(entry.practitioner)

	if entry.item_code:
		child_filter += ' and entry.drug = %(item_code)s'
		values['item_code'] = frappe.db.escape(entry.item_code)

	if entry.assigned_to_practitioner:
		parent_filter += ' and ip._assign LIKE %(assigned_to)s'
		values['assigned_to'] = '%' + entry.assigned_to_practitioner + '%'

	data = frappe.db.sql("""
		SELECT
			ip.inpatient_record, ip.patient, ip.patient_name,
			entry.name, entry.parent, entry.drug, entry.drug_name,
			entry.dosage, entry.dosage_form, entry.date, entry.time, entry.instructions
		FROM
			`tabInpatient Medication Order` ip
		INNER JOIN
			`tabInpatient Medication Order Entry` entry
		ON
			ip.name = entry.parent
		WHERE
			ip.docstatus = 1 and
			ip.company = %(company)s and
			entry.is_completed = 0
			{0} {1}
		ORDER BY
			entry.date, entry.time
		""".format(parent_filter, child_filter), values, as_dict=1)

	for doc in data:
		inpatient_record = doc.inpatient_record
		doc['service_unit'] = get_current_healthcare_service_unit(inpatient_record)

		if entry.service_unit and doc.service_unit != entry.service_unit:
			data.remove(doc)

	return data


def get_current_healthcare_service_unit(inpatient_record):
	ip_record = frappe.get_doc('Inpatient Record', inpatient_record)
	return ip_record.inpatient_occupancies[-1].service_unit