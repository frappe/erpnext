# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PendingDepreciationAsset(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset: DF.Link | None
		asset_category: DF.Link | None
		asset_name: DF.Data | None
		depreciation_method: DF.Data | None
		depr_schedule_name: DF.Data | None
		finance_book: DF.Link | None
		next_depreciation_date: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pending_depreciation_amount: DF.Currency
	# end: auto-generated types
	pass
