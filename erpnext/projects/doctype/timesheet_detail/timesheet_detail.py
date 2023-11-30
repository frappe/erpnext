# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class TimesheetDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		activity_type: DF.Link | None
		base_billing_amount: DF.Currency
		base_billing_rate: DF.Currency
		base_costing_amount: DF.Currency
		base_costing_rate: DF.Currency
		billing_amount: DF.Currency
		billing_hours: DF.Float
		billing_rate: DF.Currency
		completed: DF.Check
		costing_amount: DF.Currency
		costing_rate: DF.Currency
		description: DF.SmallText | None
		expected_hours: DF.Float
		from_time: DF.Datetime | None
		hours: DF.Float
		is_billable: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		project: DF.Link | None
		project_name: DF.Data | None
		sales_invoice: DF.Link | None
		task: DF.Link | None
		to_time: DF.Datetime | None
	# end: auto-generated types

	pass
