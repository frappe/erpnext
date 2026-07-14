# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CouponCampaign(Document):
	"""Groups coupon codes for one Pricing Scheme with redemption limits.

	Limits are enforced against the Coupon Redemption ledger at match
	time (engine gate), never via a mutable counter.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		disabled: DF.Check
		max_uses_per_customer: DF.Int
		max_uses_total: DF.Int
		pricing_scheme: DF.Link
		title: DF.Data
		valid_from: DF.Date | None
		valid_upto: DF.Date | None
	# end: auto-generated types

	def validate(self) -> None:
		self.validate_from_to_dates("valid_from", "valid_upto")
		if not frappe.get_cached_value("Pricing Scheme", self.pricing_scheme, "coupon_required"):
			frappe.throw(
				_("Pricing Scheme {0} does not have Coupon Required enabled.").format(self.pricing_scheme)
			)
