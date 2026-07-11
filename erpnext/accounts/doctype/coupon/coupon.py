# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Coupon(Document):
	"""One redeemable code within a Coupon Campaign.

	Codes are unique among *active* coupons only, so a recognizable code
	("SAVE20") can be reissued for a later season once the earlier coupon
	is disabled. Redemption history stays unambiguous because the ledger
	links this document, not the code text.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		campaign: DF.Link
		code: DF.Data
		description: DF.SmallText | None
		status: DF.Literal["Active", "Disabled"]
	# end: auto-generated types

	def validate(self) -> None:
		self.code = (self.code or "").strip().upper()
		self.validate_code_unique_among_active()

	def validate_code_unique_among_active(self) -> None:
		if self.status != "Active":
			return
		clash = frappe.db.exists("Coupon", {"code": self.code, "status": "Active", "name": ("!=", self.name)})
		if clash:
			frappe.throw(
				_(
					"An active coupon with code {0} already exists: {1}. Disable it first to reuse the code."
				).format(frappe.bold(self.code), clash)
			)
