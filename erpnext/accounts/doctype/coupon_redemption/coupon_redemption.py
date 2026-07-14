# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CouponRedemption(Document):
	"""One coupon use per order chain, atomic by construction.

	The document name is ``{coupon}::{order_chain_root}``, so the primary
	key IS the composite unique constraint: two concurrent submissions of
	the same chain cannot both insert, with no counter and no lock.
	Cancel flips status; nothing ever decrements.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		campaign: DF.Link | None
		coupon: DF.Link
		order_chain_root: DF.Data
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		posting_date: DF.Date | None
		status: DF.Literal["Redeemed", "Cancelled"]
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link | None
	# end: auto-generated types

	def autoname(self) -> None:
		self.name = f"{self.coupon}::{self.order_chain_root}"
