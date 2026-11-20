# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import today

exclude_from_linked_with = True

# Only these rows count towards the spend that decides a customer's tier.
SPEND_ENTRY_TYPES = ("Earn", "Earn Reversal")

# Type of the row that cancels a row of this type. Other types keep their own type.
REVERSE_ENTRY_TYPES = {"Earn": "Earn Reversal", "Redeem": "Redeem Reversal"}

# Fields a reverse row takes from the row it cancels, with the opposite sign.
SIGNED_FIELDS = ("loyalty_points", "purchase_amount", "amount")


class LoyaltyPointEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		company: DF.Link
		customer: DF.Link
		discretionary_reason: DF.Data | None
		earn_rate: DF.Float
		entry_type: DF.Literal[
			"", "Earn", "Redeem", "Earn Reversal", "Redeem Reversal", "Adjustment", "Opening", "Expiry"
		]
		expiry_date: DF.Date
		invoice: DF.DynamicLink | None
		invoice_type: DF.Link | None
		is_cancelled: DF.Check
		loyalty_points: DF.Int
		loyalty_program: DF.Link
		loyalty_program_tier: DF.Data | None
		posting_date: DF.Date
		purchase_amount: DF.Currency
		redeem_against: DF.Link | None
		reversal_of: DF.Link | None
	# end: auto-generated types

	def validate(self):
		if not self.entry_type:
			self.entry_type = self.get_default_entry_type()

		if self.entry_type not in SPEND_ENTRY_TYPES:
			self.purchase_amount = 0

	def get_default_entry_type(self):
		"""Type of a row written without one, for example by a custom app."""
		if self.redeem_against:
			return "Redeem"

		return "Earn" if self.invoice else "Adjustment"


def add_loyalty_point_entry(values: dict) -> LoyaltyPointEntry:
	"""Add one row to the points ledger. Rows are never changed or deleted after this."""
	entry = frappe.get_doc({"doctype": "Loyalty Point Entry", **values})
	entry.flags.ignore_permissions = True
	entry.insert()
	return entry


def make_reverse_entries(voucher_type: str, voucher_no: str) -> int:
	"""Cancel the live rows of a voucher the way GL Entry does.

	Flag each row as cancelled and add a flagged row with the opposite points. Readers that skip
	cancelled rows see neither row, and a raw sum of all rows stays correct.
	Return the number of rows cancelled.
	"""
	entries = frappe.get_all(
		"Loyalty Point Entry",
		filters={"invoice_type": voucher_type, "invoice": voucher_no, "is_cancelled": 0},
		fields=["*"],
	)
	if not entries:
		return 0

	lpe = frappe.qb.DocType("Loyalty Point Entry")
	(
		frappe.qb.update(lpe).set(lpe.is_cancelled, 1).where(lpe.name.isin([entry.name for entry in entries]))
	).run()

	for entry in entries:
		add_loyalty_point_entry(get_reverse_entry(entry))

	return len(entries)


def get_reverse_entry(entry: dict) -> dict:
	values = {
		field: entry[field]
		for field in (
			"company",
			"customer",
			"loyalty_program",
			"loyalty_program_tier",
			"invoice_type",
			"invoice",
			"redeem_against",
			"earn_rate",
			"expiry_date",
			"posting_date",
		)
	}
	values.update({field: -1 * (entry[field] or 0) for field in SIGNED_FIELDS})
	values.update(
		{
			"entry_type": REVERSE_ENTRY_TYPES.get(entry.entry_type, entry.entry_type),
			"reversal_of": entry.name,
			"is_cancelled": 1,
		}
	)
	return values


def get_loyalty_point_entries(customer, loyalty_program, company, expiry_date=None):
	if not expiry_date:
		expiry_date = today()

	return frappe.get_all(
		"Loyalty Point Entry",
		filters={
			"customer": customer,
			"loyalty_program": loyalty_program,
			"expiry_date": [">=", expiry_date],
			"loyalty_points": [">", 0],
			"company": company,
			"is_cancelled": 0,
		},
		fields=["name", "loyalty_points", "expiry_date", "loyalty_program_tier", "invoice_type", "invoice"],
		order_by="expiry_date",
	)


def get_redemption_details(customer, loyalty_program, company):
	return frappe._dict(
		frappe.get_all(
			"Loyalty Point Entry",
			filters={
				"customer": customer,
				"loyalty_program": loyalty_program,
				"loyalty_points": ["<", 0],
				"company": company,
				"is_cancelled": 0,
			},
			fields=["redeem_against", {"SUM": "loyalty_points", "as": "loyalty_points"}],
			group_by="redeem_against",
			as_list=True,
		)
	)
