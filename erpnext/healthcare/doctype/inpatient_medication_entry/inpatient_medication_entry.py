# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class InpatientMedicationEntry(Document):
	def get_medication_orders(self):
		"""Pull medication prescriptions from Patient Encounter for currently admitted patients based on selected filters"""
		orders = get_pending_medication_orders(self)

		if orders:
			self.add_mo_to_table(orders)
		else:
			self.set('medication_orders', [])
			frappe.msgprint(_('No pending medication orders found for selected criteria'))

	def add_mo_to_table(self, orders):
		"""Add medication orders in the child table"""
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
		self.update_medication_orders()

	def update_medication_orders(self):
		# for marking order entries as completed
		orders = []
		# for storing how many entries have been completed in one Inpatient Medication Order
		order_entry_map = dict()

		for entry in self.medication_orders:
			orders.append(entry.against_imoe)
			parent = entry.against_imo
			if not order_entry_map.get(parent):
				order_entry_map[parent] = 0

			order_entry_map[parent] += 1

		# mark as completed
		frappe.db.sql("""
			UPDATE `tabInpatient Medication Order Entry`
			SET is_completed = 1
			WHERE name IN %(orders)s
		""", {'orders': orders})

		# update status and completed count
		for order, count in order_entry_map.items():
			medication_order = frappe.get_doc('Inpatient Medication Order', order)
			medication_order.db_set('completed_orders', count)
			medication_order.set_status()


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
		values['patient'] = entry.patient

	if entry.practitioner:
		parent_filter += ' and ip.practitioner = %(practitioner)s'
		values['practitioner'] = entry.practitioner

	if entry.item_code:
		child_filter += ' and entry.drug = %(item_code)s'
		values['item_code'] = entry.item_code

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