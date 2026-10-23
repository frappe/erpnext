# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Delivery schedule management for Sales Order Items."""

import frappe
from frappe.utils import flt, parse_json


class DeliveryScheduleService:
	def __init__(self, doc):
		self.doc = doc

	def get_delivery_schedule(self, sales_order_item: str) -> list[dict]:
		return frappe.get_all(
			"Delivery Schedule Item",
			filters={"sales_order_item": sales_order_item, "sales_order": self.doc.name},
			fields=["delivery_date", "qty", "name"],
			order_by="delivery_date asc",
		)

	def create_delivery_schedule(self, child_row: dict | frappe._dict, schedules: str | list[dict]) -> None:
		if isinstance(child_row, dict):
			child_row = frappe._dict(child_row)

		if isinstance(schedules, str):
			schedules = parse_json(schedules)

		names = []
		first_delivery_date = None
		for row in schedules:
			row = frappe._dict(row)

			if not first_delivery_date:
				first_delivery_date = row.delivery_date

			data = {
				"delivery_date": row.delivery_date,
				"qty": row.qty,
				"uom": child_row.uom,
				"stock_uom": child_row.stock_uom,
				"item_code": child_row.item_code,
				"conversion_factor": child_row.conversion_factor or 1.0,
				"warehouse": child_row.warehouse,
				"sales_order_item": child_row.name,
				"sales_order": self.doc.name,
				"stock_qty": row.qty * (child_row.conversion_factor or 1.0),
			}

			if frappe.db.exists("Delivery Schedule Item", row.name):
				doc = frappe.get_doc("Delivery Schedule Item", row.name)
			else:
				doc = frappe.new_doc("Delivery Schedule Item")

			doc.update(data)
			doc.save(ignore_permissions=True)
			names.append(doc.name)

		if names:
			self.delete_delivery_schedule_items(child_row.name, names)

		if first_delivery_date:
			self.update_delivery_date_based_on_schedule(child_row, first_delivery_date)

	def update_delivery_date_based_on_schedule(self, child_row, first_delivery_date) -> None:
		for row in self.doc.items:
			if row.name == child_row.name:
				if first_delivery_date:
					row.delivery_date = first_delivery_date
				break

		self.doc.save()

	def sync_schedule_with_item(self, child_row) -> None:
		"""Rescale and refresh an item's schedules after its qty, UOM or conversion factor changed."""
		schedules = frappe.get_all(
			"Delivery Schedule Item",
			filters={"sales_order_item": child_row.name, "sales_order": self.doc.name},
			fields=["name", "qty"],
			order_by="delivery_date asc, creation asc",
		)
		if not schedules:
			return

		conversion_factor = child_row.conversion_factor or 1.0
		remaining = flt(child_row.qty)
		stale = []
		for schedule in schedules:
			kept_qty = min(flt(schedule.qty), remaining) if remaining > 0 else 0
			if not kept_qty:
				stale.append(schedule.name)
				continue

			remaining -= kept_qty
			frappe.db.set_value(
				"Delivery Schedule Item",
				schedule.name,
				{
					"qty": kept_qty,
					"uom": child_row.uom,
					"stock_uom": child_row.stock_uom,
					"conversion_factor": conversion_factor,
					"warehouse": child_row.warehouse,
					"stock_qty": kept_qty * conversion_factor,
				},
			)

		if stale:
			self._delete_by_name(stale)

	def _delete_by_name(self, names: list) -> None:
		doctype = frappe.qb.DocType("Delivery Schedule Item")
		frappe.qb.from_(doctype).delete().where(doctype.name.isin(names)).run()

	def delete_delivery_schedule_items(
		self, sales_order_item: str | None = None, ignore_names: list | None = None
	) -> None:
		"""Delete delivery schedule items."""
		doctype = frappe.qb.DocType("Delivery Schedule Item")

		query = frappe.qb.from_(doctype).delete().where(doctype.sales_order == self.doc.name)

		if ignore_names:
			query = query.where(doctype.name.notin(ignore_names))

		if sales_order_item:
			query = query.where(doctype.sales_order_item == sales_order_item)

		query.run()

	def delete_removed_delivery_schedule_items(self) -> None:
		items = [d.name for d in self.doc.get("items")]
		doctype = frappe.qb.DocType("Delivery Schedule Item")
		frappe.qb.from_(doctype).delete().where(
			(doctype.sales_order == self.doc.name) & (doctype.sales_order_item.notin(items))
		).run()
