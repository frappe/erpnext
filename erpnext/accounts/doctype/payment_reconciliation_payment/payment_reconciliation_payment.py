# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class PaymentReconciliationPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		cost_center: DF.Link | None
		currency: DF.Link | None
		difference_amount: DF.Currency
		exchange_rate: DF.Float
		is_advance: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		posting_date: DF.Date | None
		reference_name: DF.DynamicLink | None
		reference_row: DF.Data | None
		reference_type: DF.Link | None
		remark: DF.SmallText | None
	# end: auto-generated types

	@staticmethod
	def get_list(args):
		pass
