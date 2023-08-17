# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ServiceItemandFinishedGoodsMap(Document):
	def validate(self):
		self.validate_service_item()
		self.validate_finished_goods_detail()

	def before_save(self):
		self.set_conversion_factor()

	def validate_service_item(self):
		disabled, is_stock_item = frappe.db.get_value(
			"Item", self.service_item, ["disabled", "is_stock_item"]
		)

		if disabled:
			frappe.throw(f"Service Item {self.service_item} is disabled.")
		if is_stock_item:
			frappe.throw(f"Service Item {self.service_item} is a stock item.")

	def validate_finished_goods_detail(self):
		for fg_detail in self.finished_goods_detail:
			disabled, is_stock_item, default_bom, is_sub_contracted_item = frappe.db.get_value(
				"Item",
				fg_detail.finished_good_item,
				["disabled", "is_stock_item", "default_bom", "is_sub_contracted_item"],
			)

			if disabled:
				frappe.throw(
					_("Row {0}: Finished Good Item {1} is disabled.").format(
						fg_detail.idx, frappe.bold(fg_detail.finished_good_item)
					)
				)
			if not is_stock_item:
				frappe.throw(
					_("Row {0}: Finished Good Item {1} is not a stock item.").format(
						fg_detail.idx, frappe.bold(fg_detail.finished_good_item)
					)
				)
			if not default_bom:
				frappe.throw(
					_("Row {0}: Finished Good Item {1} does not have a default BOM.").format(
						fg_detail.idx, frappe.bold(fg_detail.finished_good_item)
					)
				)
			if not is_sub_contracted_item:
				frappe.throw(
					_("Row {0}: Finished Good Item {1} is not a sub-contracted item.").format(
						fg_detail.idx, frappe.bold(fg_detail.finished_good_item)
					)
				)

	def set_conversion_factor(self):
		for fg_detail in self.finished_goods_detail:
			fg_detail.conversion_factor = flt(self.service_item_qty) / flt(fg_detail.finished_good_qty)


@frappe.whitelist()
def get_service_items_for_finished_goods(fg_items: str | list) -> dict:
	if fg_items:
		parent = frappe.qb.DocType("Service Item and Finished Goods Map")
		child = frappe.qb.DocType("Finished Good Detail")

		query = (
			frappe.qb.from_(parent)
			.inner_join(child)
			.on(parent.name == child.parent)
			.select(
				parent.service_item,
				parent.service_item_uom,
				child.finished_good_item,
				child.conversion_factor,
			)
			.where(parent.is_active == 1)
		)

		if isinstance(fg_items, list):
			query = query.where(child.finished_good_item.isin(fg_items))
		else:
			query = query.where(child.finished_good_item == fg_items)

		if service_item_details := query.run(as_dict=True):
			if isinstance(fg_items, list):
				return {d.finished_good_item: d for d in service_item_details}
			else:
				return service_item_details[0]

	return {}
