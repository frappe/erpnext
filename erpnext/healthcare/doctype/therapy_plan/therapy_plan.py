# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

class TherapyPlan(Document):
	def validate(self):
		self.set_totals()
		self.set_status()

	def set_status(self):
		if not self.total_sessions_completed:
			self.status = 'Not Started'
		else:
			if self.total_sessions_completed < self.total_sessions:
				self.status = 'In Progress'
			elif self.total_sessions_completed == self.total_sessions:
				self.status = 'Completed'

	def set_totals(self):
		total_sessions = 0
		total_sessions_completed = 0
		for entry in self.therapy_plan_details:
			if entry.no_of_sessions:
				total_sessions += entry.no_of_sessions
			if entry.sessions_completed:
				total_sessions_completed += entry.sessions_completed

		self.db_set('total_sessions', total_sessions)
		self.db_set('total_sessions_completed', total_sessions_completed)

	def set_therapy_details_from_template(self):
		# Add therapy types in the child table
		self.set('therapy_plan_details', [])
		therapy_plan_template = frappe.get_doc('Therapy Plan Template', self.therapy_plan_template)

		for data in therapy_plan_template.therapy_types:
			self.append('therapy_plan_details', {
				'therapy_type': data.therapy_type,
				'no_of_sessions': data.no_of_sessions
			})
		return self


@frappe.whitelist()
def make_therapy_session(therapy_plan, patient, therapy_type, company, appointment=None):
	therapy_type = frappe.get_doc('Therapy Type', therapy_type)

	therapy_session = frappe.new_doc('Therapy Session')
	therapy_session.therapy_plan = therapy_plan
	therapy_session.company = company
	therapy_session.patient = patient
	therapy_session.therapy_type = therapy_type.name
	therapy_session.duration = therapy_type.default_duration
	therapy_session.rate = therapy_type.rate
	therapy_session.exercises = therapy_type.exercises
	therapy_session.appointment = appointment

	if frappe.flags.in_test:
		therapy_session.start_date = today()
	return therapy_session.as_dict()


@frappe.whitelist()
def make_sales_invoice(reference_name, patient, company, therapy_plan_template):
	from erpnext.stock.get_item_details import get_item_details
	si = frappe.new_doc('Sales Invoice')
	si.company = company
	si.patient = patient
	si.customer = frappe.db.get_value('Patient', patient, 'customer')

	item = frappe.db.get_value('Therapy Plan Template', therapy_plan_template, 'linked_item')
	price_list, price_list_currency = frappe.db.get_values('Price List', {'selling': 1}, ['name', 'currency'])[0]
	args = {
		'doctype': 'Sales Invoice',
		'item_code': item,
		'company': company,
		'customer': si.customer,
		'selling_price_list': price_list,
		'price_list_currency': price_list_currency,
		'plc_conversion_rate': 1.0,
		'conversion_rate': 1.0
	}

	item_line = si.append('items', {})
	item_details = get_item_details(args)
	item_line.item_code = item
	item_line.qty = 1
	item_line.rate = item_details.price_list_rate
	item_line.amount = flt(item_line.rate) * flt(item_line.qty)
	item_line.reference_dt = 'Therapy Plan'
	item_line.reference_dn = reference_name
	item_line.description = item_details.description

	si.set_missing_values(for_validate = True)
	return si
