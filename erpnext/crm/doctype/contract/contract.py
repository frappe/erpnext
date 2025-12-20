# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class Contract(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.crm.doctype.contract_fulfilment_checklist.contract_fulfilment_checklist import (
			ContractFulfilmentChecklist,
		)

		amended_from: DF.Link | None
		contract_template: DF.Link | None
		contract_terms: DF.TextEditor
		document_name: DF.DynamicLink | None
		document_type: DF.Literal[
			"", "Quotation", "Project", "Sales Order", "Purchase Order", "Sales Invoice", "Purchase Invoice"
		]
		end_date: DF.Date | None
		fulfilment_deadline: DF.Date | None
		fulfilment_status: DF.Literal["N/A", "Unfulfilled", "Partially Fulfilled", "Fulfilled", "Lapsed"]
		fulfilment_terms: DF.Table[ContractFulfilmentChecklist]
		ip_address: DF.Data | None
		is_signed: DF.Check
		party_full_name: DF.Data | None
		party_name: DF.DynamicLink
		party_type: DF.Literal["Customer", "Supplier", "Employee"]
		party_user: DF.Link | None
		requires_fulfilment: DF.Check
		signed_by_company: DF.Link | None
		signed_on: DF.Datetime | None
		signee: DF.Data | None
		start_date: DF.Date | None
		status: DF.Literal["Unsigned", "Active", "Inactive"]
	# end: auto-generated types

	def validate(self):
		self.set_missing_values()
		self.validate_dates()
		self.update_contract_status()
		self.update_fulfilment_status()

	def set_missing_values(self):
		if not self.party_full_name:
			field = self.party_type.lower() + "_name"
			if res := frappe.db.get_value(self.party_type, self.party_name, field):
				self.party_full_name = res

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

	contracts = frappe.get_all(
		"Contract",
		filters={"is_signed": True, "docstatus": 1},
		fields=["name", "start_date", "end_date"],
	)

	for contract in contracts:
		status = get_status(contract.get("start_date"), contract.get("end_date"))

		frappe.db.set_value("Contract", contract.get("name"), "status", status)
