# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LeaseTermination(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accumulated_depreciation: DF.Currency
		amended_from: DF.Link | None
		gainloss: DF.Currency
		lease_agreement: DF.Link | None
		penalty_account: DF.Link | None
		remaining_liability: DF.Currency
		rou_asset_gross: DF.Currency
		rou_net_book_value: DF.Currency
		termination_date: DF.Date | None
		termination_journal_entry: DF.Link | None
		termination_penalty: DF.Currency
		termination_reason: DF.SmallText | None
	# end: auto-generated types

	pass
