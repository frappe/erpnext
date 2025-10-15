# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubcontractingInwardOrderReceivedItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		billed_qty: DF.Float
		bom_detail_no: DF.Data | None
		consumed_qty: DF.Float
		is_additional_item: DF.Check
		is_customer_provided_item: DF.Check
		main_item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		received_qty: DF.Float
		reference_name: DF.Data | None
		required_qty: DF.Float
		returned_qty: DF.Float
		rm_item_code: DF.Link
		stock_uom: DF.Link
		warehouse: DF.Link | None
		work_order_qty: DF.Float
	# end: auto-generated types

	pass
