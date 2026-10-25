# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.permissions import filter_allowed_docs_for_doctype, get_user_permissions, get_valid_perms
from frappe.utils import get_datetime, getdate, nowdate
from pypika.terms import Criterion

ROLE_PARTY_TYPES = {"Sales Manager": "Customer", "Purchase Manager": "Supplier", "HR Manager": "Employee"}


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
		status: DF.Literal["Unsigned", "Active", "Inactive", "Cancelled"]
	# end: auto-generated types

	def validate(self):
		self.set_missing_values()
		self.validate_dates()
		self.validate_signature()
		self.validate_document_party()
		self.update_contract_status()
		self.update_fulfilment_status()

	def set_missing_values(self):
		if (
			not self.party_full_name
			or self.has_value_changed("party_name")
			or self.has_value_changed("party_type")
		):
			field = self.party_type.lower() + "_name"
			if res := frappe.db.get_value(self.party_type, self.party_name, field):
				self.party_full_name = res

	def before_submit(self):
		self.signed_by_company = frappe.session.user

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def before_update_after_submit(self):
		self.validate_signature()
		self.validate_signature_unchanged()
		self.validate_fulfilment_terms_unchanged()
		self.update_contract_status()
		self.update_fulfilment_status()

	def validate_document_party(self):
		if not (self.document_type and self.document_name) or self.party_type == "Employee":
			return

		party = self.get_document_party()
		if party and party != self.party_name:
			frappe.throw(
				_("{0} {1} is for {2} {3}, not {4}").format(
					_(self.document_type),
					frappe.bold(self.document_name),
					_(self.party_type),
					frappe.bold(party),
					frappe.bold(self.party_name),
				)
			)

	def get_document_party(self) -> str | None:
		if self.document_type == "Quotation":
			quotation_to, party = frappe.db.get_value(
				"Quotation", self.document_name, ["quotation_to", "party_name"]
			)
			return party if quotation_to == self.party_type else None

		field = frappe.scrub(self.party_type)
		if frappe.get_meta(self.document_type).has_field(field):
			return frappe.db.get_value(self.document_type, self.document_name, field)

	def validate_signature(self):
		if self.is_signed and not (self.signee and self.signed_on):
			frappe.throw(_("Signee and Signed On are required for a signed contract."))

	def validate_signature_unchanged(self):
		"""A submitted contract can be signed later, but not unsigned or re-signed: amend it instead."""
		previous = self.get_doc_before_save()
		if not (previous and previous.is_signed):
			return

		# details missing on older signed contracts can still be filled in
		if (
			not self.is_signed
			or (previous.signee and self.signee != previous.signee)
			or (previous.signed_on and get_datetime(self.signed_on) != get_datetime(previous.signed_on))
		):
			frappe.throw(
				_("The signature of a signed contract cannot be changed. Amend the contract instead."),
				frappe.UpdateAfterSubmitError,
			)

	def validate_fulfilment_terms_unchanged(self):
		"""Rows can be ticked after submit, not added or removed."""
		previous = self.get_doc_before_save()
		if previous and {row.name for row in previous.fulfilment_terms} != {
			row.name for row in self.fulfilment_terms
		}:
			frappe.throw(
				_("Fulfilment terms cannot be added or removed after submission."),
				frappe.UpdateAfterSubmitError,
			)

	def validate_dates(self):
		if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
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


class ContractPartyAccess:
	"""Limits contracts to the party types of the user's roles and to the parties in their User Permissions."""

	def __init__(self, user: str | None = None):
		self.user = user or frappe.session.user
		self.meta = frappe.get_meta("Contract")
		self.all_party_types = self.meta.get_field("party_type").options.split("\n")
		self.party_types = self.get_party_types()
		self.allowed_parties = {
			party_type: self.get_allowed_parties(party_type) for party_type in self.party_types
		}

	def has_access(self, party_type: str | None, party_name: str | None) -> bool:
		if not party_type:
			return True

		if party_type not in self.party_types:
			return False

		allowed_parties = self.allowed_parties[party_type]
		return not (allowed_parties and party_name) or party_name in allowed_parties

	def get_criterion(self) -> Criterion | None:
		if self.party_types == self.all_party_types and not any(self.allowed_parties.values()):
			return None

		contract = frappe.qb.DocType("Contract")
		return Criterion.any(
			[self.get_party_criterion(contract, party_type) for party_type in self.party_types]
		)

	def get_party_criterion(self, contract, party_type: str) -> Criterion:
		criterion = contract.party_type == party_type
		if allowed_parties := self.allowed_parties[party_type]:
			criterion &= contract.party_name.isin(allowed_parties)

		return criterion

	def get_party_types(self) -> list[str]:
		"""Roles not mapped in ROLE_PARTY_TYPES, like System Manager, give access to all party types."""
		roles = {permission.role for permission in get_valid_perms("Contract", user=self.user)}
		if self.user == "Administrator" or not roles or roles - ROLE_PARTY_TYPES.keys():
			return self.all_party_types

		party_types = {ROLE_PARTY_TYPES[role] for role in roles}
		return [party_type for party_type in self.all_party_types if party_type in party_types]

	def get_allowed_parties(self, party_type: str) -> list[str]:
		if self.meta.get_field("party_name").ignore_user_permissions:
			return []

		user_permissions = get_user_permissions(self.user).get(party_type, [])
		return filter_allowed_docs_for_doctype(user_permissions, "Contract", with_default_doc=False)


def get_status(start_date, end_date):
	"""
	Get a Contract's status based on the start, current and end dates

	Args:
	        start_date (str): The start date of the contract
	        end_date (str): The end date of the contract

	Returns:
	        str: 'Active' if within range, otherwise 'Inactive'
	"""

	now_date = getdate(nowdate())
	if start_date and getdate(start_date) > now_date:
		return "Inactive"

	# a blank end date means the contract is open-ended
	if end_date and getdate(end_date) < now_date:
		return "Inactive"

	return "Active"


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

	set_lapsed_fulfilment_status()


def set_lapsed_fulfilment_status():
	"""Mark submitted contracts whose fulfilment deadline passed unfulfilled as Lapsed."""
	frappe.db.set_value(
		"Contract",
		{
			"docstatus": 1,
			"requires_fulfilment": 1,
			"fulfilment_deadline": ("<", nowdate()),
			"fulfilment_status": ("not in", ["Fulfilled", "Lapsed"]),
		},
		"fulfilment_status",
		"Lapsed",
	)


def has_permission(doc: Contract, ptype: str | None = None, user: str | None = None) -> bool:
	return ContractPartyAccess(user).has_access(doc.party_type, doc.party_name)


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> Criterion | None:
	return ContractPartyAccess(user).get_criterion()
