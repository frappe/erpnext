# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Party validation: PartyValidator class for transaction-level party checks."""

import frappe
from frappe import _

from erpnext.accounts.party import (
	get_party_account_currency,
	get_party_gle_currency,
	validate_party_frozen_disabled,
)
from erpnext.accounts.utils import get_account_currency
from erpnext.exceptions import InvalidCurrency


class PartyValidator:
	"""Validates all party-related fields on a transaction document."""

	def __init__(self, doc):
		self.doc = doc

	def validate(self) -> None:
		"""Run all party-related validations in order."""
		self.validate_party()
		self.validate_party_accounts()
		self.validate_currency()
		self.validate_party_account_currency()
		self.validate_address_and_contact()
		self.validate_company_linked_addresses()

	def get_party(self) -> tuple[str | None, str | None]:
		"""Return (party_type, party_name) for the document."""
		doc = self.doc
		party_type = None

		if doc.doctype in ("Opportunity", "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"):
			party_type = "Customer"
		elif doc.doctype in (
			"Supplier Quotation",
			"Purchase Order",
			"Purchase Receipt",
			"Purchase Invoice",
		):
			party_type = "Supplier"
		elif doc.meta.get_field("customer"):
			party_type = "Customer"
		elif doc.meta.get_field("supplier"):
			party_type = "Supplier"

		party = doc.get(party_type.lower()) if party_type else None
		return party_type, party

	def validate_party(self) -> None:
		party_type, party = self.get_party()
		validate_party_frozen_disabled(self.doc.company, party_type, party)

	def validate_party_accounts(self) -> None:
		if self.doc.doctype not in ("Sales Invoice", "Purchase Invoice"):
			return

		if self.doc.doctype == "Sales Invoice":
			party_account_field = "debit_to"
			item_field = "income_account"
		else:
			party_account_field = "credit_to"
			item_field = "expense_account"

		for item in self.doc.get("items"):
			if item.get(item_field) == self.doc.get(party_account_field):
				frappe.throw(
					_("Row {0}: {1} {2} cannot be same as {3} (Party Account) {4}").format(
						item.idx,
						frappe.bold(frappe.unscrub(item_field)),
						item.get(item_field),
						frappe.bold(frappe.unscrub(party_account_field)),
						self.doc.get(party_account_field),
					)
				)

	def validate_currency(self) -> None:
		if not self.doc.get("currency"):
			return

		party_type, party = self.get_party()
		if not (party_type and party):
			return

		party_account_currency = get_party_account_currency(party_type, party, self.doc.company)

		if (
			party_account_currency
			and party_account_currency != self.doc.company_currency
			and self.doc.currency != party_account_currency
		):
			frappe.throw(
				_("Accounting Entry for {0}: {1} can only be made in currency: {2}").format(
					party_type, party, party_account_currency
				),
				InvalidCurrency,
			)

	def validate_party_account_currency(self) -> None:
		if self.doc.doctype not in ("Sales Invoice", "Purchase Invoice"):
			return
		if self.doc.is_opening == "Yes":
			return

		party_type, party = self.get_party()
		party_gle_currency = get_party_gle_currency(party_type, party, self.doc.company)
		party_account = (
			self.doc.get("debit_to") if self.doc.doctype == "Sales Invoice" else self.doc.get("credit_to")
		)
		party_account_currency = get_account_currency(party_account)
		allow_multi_currency = frappe.db.get_singles_value(
			"Accounts Settings", "allow_multi_currency_invoices_against_single_party_account"
		)

		if (
			not party_gle_currency
			and party_account_currency != self.doc.currency
			and not allow_multi_currency
		):
			frappe.throw(
				_("Party Account {0} currency ({1}) and document currency ({2}) should be same").format(
					frappe.bold(party_account), party_account_currency, self.doc.currency
				)
			)

	def validate_address_and_contact(self) -> None:
		party_type, party = self.get_party()
		if not (party_type and party):
			return

		if party_type == "Customer":
			self._validate_address(
				party,
				party_type,
				self.doc.get("customer_address"),
				self.doc.get("shipping_address_name"),
			)
		elif party_type == "Supplier":
			self._validate_address(party, party_type, self.doc.get("supplier_address"))

		self._validate_contact(party, party_type)

	def validate_company_linked_addresses(self) -> None:
		doc = self.doc
		sales_doctypes = ("Quotation", "Sales Order", "Delivery Note", "Sales Invoice")
		purchase_doctypes = ("Purchase Order", "Purchase Receipt", "Purchase Invoice", "Supplier Quotation")

		if doc.doctype in sales_doctypes:
			address_fields = ["dispatch_address_name", "company_address"]
		elif doc.doctype in purchase_doctypes:
			address_fields = ["billing_address", "shipping_address"]
		else:
			return

		is_drop_ship = (
			doc.doctype
			in {
				"Purchase Order",
				"Purchase Invoice",
				"Sales Order",
				"Sales Invoice",
			}
			and self._is_drop_ship()
		)

		for field in address_fields:
			address = doc.get(field)
			if field in ("dispatch_address_name", "shipping_address") and is_drop_ship:
				continue
			if address and not frappe.db.exists(
				"Dynamic Link",
				{
					"parent": address,
					"parenttype": "Address",
					"link_doctype": "Company",
					"link_name": doc.company,
				},
			):
				frappe.throw(
					_("{0} does not belong to the Company {1}.").format(
						_(doc.meta.get_label(field)), frappe.bold(doc.company)
					)
				)

	def _validate_address(
		self,
		party: str,
		party_type: str,
		billing_address: str | None,
		shipping_address: str | None = None,
	) -> None:
		if not (billing_address or shipping_address):
			return

		party_addresses = frappe.get_all(
			"Dynamic Link",
			{"link_doctype": party_type, "link_name": party, "parenttype": "Address"},
			pluck="parent",
		)
		if billing_address and billing_address not in party_addresses:
			frappe.throw(_("Billing Address does not belong to the {0}").format(party))
		elif shipping_address and shipping_address not in party_addresses:
			frappe.throw(_("Shipping Address does not belong to the {0}").format(party))

	def _validate_contact(self, party: str, party_type: str) -> None:
		if not self.doc.get("contact_person"):
			return

		contacts = frappe.get_all(
			"Dynamic Link",
			{"link_doctype": party_type, "link_name": party, "parenttype": "Contact"},
			pluck="parent",
		)
		if self.doc.contact_person not in contacts:
			frappe.throw(_("Contact Person does not belong to the {0}").format(party))

	def _is_drop_ship(self) -> bool:
		return any(item.delivered_by_supplier for item in self.doc.items)
