# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class ItemLeadTime(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.item_lead_time_supplier.item_lead_time_supplier import (
			ItemLeadTimeSupplier,
		)

		buffer_time: DF.Int
		capacity_per_day: DF.Int
		daily_yield: DF.Percent
		item_code: DF.Link | None
		item_name: DF.Data | None
		manufacturing_time_in_mins: DF.Int
		no_of_shift: DF.Int
		no_of_units_produced: DF.Int
		no_of_workstations: DF.Int
		purchase_time: DF.Int
		shift_time_in_hours: DF.Int
		stock_uom: DF.Link | None
		supplier_lead_times: DF.Table[ItemLeadTimeSupplier]
		total_workstation_time: DF.Int
	# end: auto-generated types

	def validate(self):
		self.validate_supplier_lead_times()

	def validate_supplier_lead_times(self):
		suppliers = set()
		default_rows = 0
		for row in self.supplier_lead_times:
			if row.supplier in suppliers:
				frappe.throw(
					_("Row #{0}: Supplier {1} is already added in the Supplier Lead Times table").format(
						row.idx, frappe.bold(row.supplier)
					)
				)
			suppliers.add(row.supplier)
			default_rows += cint(row.is_default)

		if default_rows > 1:
			frappe.throw(_("Only one supplier can be marked as default in the Supplier Lead Times table"))
