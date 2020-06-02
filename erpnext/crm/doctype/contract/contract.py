# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate


class Contract(Document):
	def autoname(self):
		name = self.party_name

		if self.contract_template:
			name += " - {} Agreement".format(self.contract_template)

		# If identical, append contract name with the next number in the iteration
		if frappe.db.exists("Contract", name):
			count = len(frappe.get_all("Contract", filters={"name": ["like", "%{}%".format(name)]}))
			name = "{} - {}".format(name, count)

		self.name = _(name)

	def validate(self):
		self.validate_dates()
		self.update_contract_status()
		self.update_fulfilment_status()

	def before_submit(self):
		self.signed_by_company = frappe.session.user

	def before_update_after_submit(self):
		self.update_contract_status()
		self.update_fulfilment_status()

	def validate_dates(self):
		if self.end_date and self.end_date < self.start_date:
			frappe.throw(_("End Date cannot be before Start Date."))

	def update_contract_status(self):
		if self.is_signed:
			self.status = get_status(self.start_date, self.end_date)
		else:
			self.status = "Unsigned"

	def update_fulfilment_status(self):
		fulfilment_status = "N/A"

		if self.requires_fulfilment:
			fulfilment_progress = self.get_fulfilment_progress()

			if not fulfilment_progress:
				fulfilment_status = "Unfulfilled"
			elif fulfilment_progress < len(self.fulfilment_terms):
				fulfilment_status = "Partially Fulfilled"
			elif fulfilment_progress == len(self.fulfilment_terms):
				fulfilment_status = "Fulfilled"

			if fulfilment_status != "Fulfilled" and self.fulfilment_deadline:
				now_date = getdate(nowdate())
				deadline_date = getdate(self.fulfilment_deadline)

				if now_date > deadline_date:
					fulfilment_status = "Lapsed"

		self.fulfilment_status = fulfilment_status

	def get_fulfilment_progress(self):
		return len([term for term in self.fulfilment_terms if term.fulfilled])


def get_status(start_date, end_date):
	"""
	Get a Contract's status based on the start, current and end dates

	Args:
		start_date (str): The start date of the contract
		end_date (str): The end date of the contract

	Returns:
		str: 'Active' if within range, otherwise 'Inactive'
	"""

	if not end_date:
		return "Active"

	start_date = getdate(start_date)
	end_date = getdate(end_date)
	now_date = getdate(nowdate())

	return "Active" if start_date <= now_date <= end_date else "Inactive"


def update_status_for_contracts():
	"""
	Run the daily hook to update the statuses for all signed
	and submitted Contracts
	"""

	contracts = frappe.get_all("Contract",
								filters={"is_signed": True,
										"docstatus": 1},
								fields=["name", "start_date", "end_date"])

	for contract in contracts:
		status = get_status(contract.get("start_date"),
							contract.get("end_date"))

		frappe.db.set_value("Contract", contract.get("name"), "status", status)
