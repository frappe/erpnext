# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import add_to_date


class SalesForecast(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.sales_forecast_item.sales_forecast_item import SalesForecastItem

		amended_from: DF.Link | None
		company: DF.Link
		demand_number: DF.Int
		frequency: DF.Literal["Weekly", "Monthly"]
		from_date: DF.Date
		items: DF.Table[SalesForecastItem]
		naming_series: DF.Literal["SF.YY.-.######"]
		parent_warehouse: DF.Link
		posting_date: DF.Date | None
		selected_items: DF.TableMultiSelect[SalesForecastItem]
		status: DF.Literal["Planned", "MPS Generated", "Cancelled"]
	# end: auto-generated types

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def generate_manual_demand(self):
		forecast_demand = []
		for row in self.selected_items:
			item_details = frappe.db.get_value(
				"Item", row.item_code, ["item_name", "stock_uom as uom"], as_dict=True
			)

			for index in range(self.demand_number):
				if self.frequency == "Monthly":
					delivery_date = add_to_date(self.from_date, months=index + 1)
				else:
					delivery_date = add_to_date(self.from_date, weeks=index + 1)

				forecast_demand.append(
					{
						"item_code": row.item_code,
						"delivery_date": delivery_date,
						"item_name": item_details.item_name,
						"uom": item_details.uom,
						"demand_qty": 1.0,
					}
				)

		for demand in forecast_demand:
			self.append("items", demand)

	@frappe.whitelist()
	def generate_demand(self):
		self.set("items", [])
		self.generate_manual_demand()


@frappe.whitelist()
def create_mps(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.naming_series = "MPS.YY.-.######"

	doc = get_mapped_doc(
		"Sales Forecast",
		source_name,
		{
			"Sales Forecast": {
				"doctype": "Master Production Schedule",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {
					"name": "sales_forecast",
					"from_date": "from_date",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doc
