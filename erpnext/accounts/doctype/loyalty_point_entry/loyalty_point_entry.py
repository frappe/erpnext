# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import today

exclude_from_linked_with = True


class LoyaltyPointEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link
		customer: DF.Link
		discretionary_reason: DF.Data | None
		expiry_date: DF.Date
		invoice: DF.DynamicLink | None
		invoice_type: DF.Link
		loyalty_points: DF.Int
		loyalty_program: DF.Link
		loyalty_program_tier: DF.Data | None
		posting_date: DF.Date
		purchase_amount: DF.Currency
		redeem_against: DF.Link | None
	# end: auto-generated types

	pass


def get_loyalty_point_entries(customer, loyalty_program, company, expiry_date=None):
	if not expiry_date:
		expiry_date = today()

	return frappe.db.sql(
		"""
		select name, loyalty_points, expiry_date, loyalty_program_tier, invoice_type, invoice
		from `tabLoyalty Point Entry`
		where customer=%s and loyalty_program=%s
			and expiry_date>=%s and loyalty_points>0 and company=%s
		order by expiry_date
	""",
		(customer, loyalty_program, expiry_date, company),
		as_dict=1,
	)


def get_redemption_details(customer, loyalty_program, company):
	return frappe._dict(
		frappe.db.sql(
			"""
		select redeem_against, sum(loyalty_points)
		from `tabLoyalty Point Entry`
		where customer=%s and loyalty_program=%s and loyalty_points<0 and company=%s
		group by redeem_against
	""",
			(customer, loyalty_program, company),
		)
	)
