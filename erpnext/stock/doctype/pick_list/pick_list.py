# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from collections import OrderedDict, defaultdict
from itertools import groupby

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.model.mapper import map_child_doc
from frappe.query_builder import Case
from frappe.query_builder.custom import GROUP_CONCAT
from frappe.query_builder.functions import Coalesce, Locate, Replace, Sum
from frappe.utils import ceil, cint, floor, flt, get_link_to_form
from frappe.utils.nestedset import get_descendants_of

from erpnext.selling.doctype.sales_order.sales_order import (
	make_delivery_note as create_delivery_note_from_sales_order,
)
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	get_auto_batch_nos,
	get_picked_serial_nos,
)
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.serial_batch_bundle import (
	SerialBatchCreation,
	get_batches_from_bundle,
	get_serial_nos_from_bundle,
)

# TODO: Prioritize SO or WO group warehouse


class PickList(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.pick_list_item.pick_list_item import PickListItem

		amended_from: DF.Link | None
		company: DF.Link
		consider_rejected_warehouses: DF.Check
		customer: DF.Link | None
		customer_name: DF.Data | None
		for_qty: DF.Float
		group_same_items: DF.Check
		ignore_pricing_rule: DF.Check
		locations: DF.Table[PickListItem]
		material_request: DF.Link | None
		naming_series: DF.Literal["STO-PICK-.YYYY.-"]
		parent_warehouse: DF.Link | None
		pick_manually: DF.Check
		prompt_qty: DF.Check
		purpose: DF.Literal["Material Transfer for Manufacture", "Material Transfer", "Delivery"]
		scan_barcode: DF.Data | None
		scan_mode: DF.Check
		status: DF.Literal["Draft", "Open", "Completed", "Cancelled"]
		work_order: DF.Link | None
	# end: auto-generated types

	def onload(self) -> None:
		if frappe.get_cached_value("Stock Settings", None, "enable_stock_reservation"):
			if self.has_unreserved_stock():
				self.set_onload("has_unreserved_stock", True)

		if self.has_reserved_stock():
			self.set_onload("has_reserved_stock", True)

	def validate(self):
		self.validate_for_qty()
		if self.pick_manually and self.get("locations"):
			self.validate_stock_qty()
			self.check_serial_no_status()

	def before_save(self):
		self.update_status()
		if not self.pick_manually:
			self.set_item_locations()

		if self.get("locations"):
			self.validate_sales_order_percentage()

	def validate_stock_qty(self):
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		for row in self.get("locations"):
			if row.batch_no and not row.qty:
				batch_qty = get_batch_qty(row.batch_no, row.warehouse, row.item_code)

				if row.qty > batch_qty:
					frappe.throw(
						_(
							"At Row #{0}: The picked quantity {1} for the item {2} is greater than available stock {3} for the batch {4} in the warehouse {5}."
						).format(row.idx, row.item_code, batch_qty, row.batch_no, bold(row.warehouse)),
						title=_("Insufficient Stock"),
					)

				continue

			bin_qty = frappe.db.get_value(
				"Bin",
				{"item_code": row.item_code, "warehouse": row.warehouse},
				"actual_qty",
			)

			if row.qty > flt(bin_qty):
				frappe.throw(
					_(
						"At Row #{0}: The picked quantity {1} for the item {2} is greater than available stock {3} in the warehouse {4}."
					).format(row.idx, row.qty, bold(row.item_code), bin_qty, bold(row.warehouse)),
					title=_("Insufficient Stock"),
				)

	def check_serial_no_status(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		for row in self.get("locations"):
			if not row.serial_no:
				continue

			picked_serial_nos = get_serial_nos(row.serial_no)
			validated_serial_nos = frappe.get_all(
				"Serial No",
				filters={"name": ("in", picked_serial_nos), "warehouse": row.warehouse},
				pluck="name",
			)

			incorrect_serial_nos = set(picked_serial_nos) - set(validated_serial_nos)
			if incorrect_serial_nos:
				frappe.throw(
					_("The Serial No at Row #{0}: {1} is not available in warehouse {2}.").format(
						row.idx, ", ".join(incorrect_serial_nos), row.warehouse
					),
					title=_("Incorrect Warehouse"),
				)

	def validate_sales_order_percentage(self):
		# set percentage picked in SO
		for location in self.get("locations"):
			if (
				location.sales_order
				and frappe.db.get_value("Sales Order", location.sales_order, "per_picked", cache=True) == 100
			):
				frappe.throw(
					_("Row #{}: item {} has been picked already.").format(location.idx, location.item_code)
				)

	def before_submit(self):
		self.validate_sales_order()
		self.validate_picked_items()

	def validate_sales_order(self):
		"""Raises an exception if the `Sales Order` has reserved stock."""

		if self.purpose != "Delivery":
			return

		so_list = set(location.sales_order for location in self.locations if location.sales_order)

		if so_list:
			for so in so_list:
				so_doc = frappe.get_doc("Sales Order", so)
				for item in so_doc.items:
					if item.stock_reserved_qty > 0:
						frappe.throw(
							_(
								"Cannot create a pick list for Sales Order {0} because it has reserved stock. Please unreserve the stock in order to create a pick list."
							).format(frappe.bold(so))
						)

	def validate_picked_items(self):
		for item in self.locations:
			if self.scan_mode and item.picked_qty < item.stock_qty:
				frappe.throw(
					_(
						"Row {0} picked quantity is less than the required quantity, additional {1} {2} required."
					).format(item.idx, item.stock_qty - item.picked_qty, item.stock_uom),
					title=_("Pick List Incomplete"),
				)

			if not self.scan_mode and item.picked_qty == 0:
				# if the user has not entered any picked qty, set it to stock_qty, before submit
				item.picked_qty = item.stock_qty

	def on_submit(self):
		self.validate_serial_and_batch_bundle()
		self.make_bundle_using_old_serial_batch_fields()
		self.update_status()
		self.update_bundle_picked_qty()
		self.update_reference_qty()
		self.update_sales_order_picking_status()

	def make_bundle_using_old_serial_batch_fields(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		for row in self.locations:
			if not row.serial_no and not row.batch_no:
				continue

			if not row.use_serial_batch_fields and (row.serial_no or row.batch_no):
				frappe.throw(_("Please enable Use Old Serial / Batch Fields to make_bundle"))

			if row.use_serial_batch_fields and (not row.serial_and_batch_bundle):
				sn_doc = SerialBatchCreation(
					{
						"item_code": row.item_code,
						"warehouse": row.warehouse,
						"voucher_type": self.doctype,
						"voucher_no": self.name,
						"voucher_detail_no": row.name,
						"qty": row.stock_qty,
						"type_of_transaction": "Outward",
						"company": self.company,
						"serial_nos": get_serial_nos(row.serial_no) if row.serial_no else None,
						"batches": frappe._dict({row.batch_no: row.stock_qty}) if row.batch_no else None,
						"batch_no": row.batch_no,
					}
				).make_serial_and_batch_bundle()

				row.serial_and_batch_bundle = sn_doc.name
				row.db_set("serial_and_batch_bundle", sn_doc.name)

	def on_update_after_submit(self) -> None:
		if self.has_reserved_stock():
			msg = _(
				"The Pick List having Stock Reservation Entries cannot be updated. If you need to make changes, we recommend canceling the existing Stock Reservation Entries before updating the Pick List."
			)
			frappe.throw(msg)

	def on_cancel(self):
		self.ignore_linked_doctypes = [
			"Serial and Batch Bundle",
			"Stock Reservation Entry",
			"Delivery Note",
		]

		self.update_status()
		self.update_bundle_picked_qty()
		self.update_reference_qty()
		self.update_sales_order_picking_status()
		self.delink_serial_and_batch_bundle()

	def delink_serial_and_batch_bundle(self):
		for row in self.locations:
			if (
				row.serial_and_batch_bundle
				and frappe.db.get_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "docstatus")
				== 1
			):
				frappe.db.set_value(
					"Serial and Batch Bundle",
					row.serial_and_batch_bundle,
					{"is_cancelled": 1, "voucher_no": ""},
				)

				frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle).cancel()
				row.db_set("serial_and_batch_bundle", None)

	def on_update(self):
		if self.get("locations"):
			self.linked_serial_and_batch_bundle()

	def linked_serial_and_batch_bundle(self):
		for row in self.get("locations"):
			if row.serial_and_batch_bundle:
				frappe.get_doc(
					"Serial and Batch Bundle", row.serial_and_batch_bundle
				).set_serial_and_batch_values(self, row)

	def on_trash(self):
		self.remove_serial_and_batch_bundle()

	def remove_serial_and_batch_bundle(self):
		for row in self.locations:
			if row.serial_and_batch_bundle:
				frappe.delete_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)

	def validate_serial_and_batch_bundle(self):
		for row in self.locations:
			if row.serial_and_batch_bundle:
				doc = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
				if doc.docstatus == 0:
					doc.submit()

	def update_status(self, status=None, update_modified=True):
		if not status:
			if self.docstatus == 0:
				status = "Draft"
			elif self.docstatus == 1:
				if target_document_exists(self.name, self.purpose):
					status = "Completed"
				else:
					status = "Open"
			elif self.docstatus == 2:
				status = "Cancelled"

		if status:
			self.db_set("status", status)

	def update_reference_qty(self):
		packed_items = []
		so_items = []

		for item in self.locations:
			if item.product_bundle_item:
				packed_items.append(item.sales_order_item)
			elif item.sales_order_item:
				so_items.append(item.sales_order_item)

		if packed_items:
			self.update_packed_items_qty(packed_items)

		if so_items:
			self.update_sales_order_item_qty(so_items)

	def update_packed_items_qty(self, packed_items):
		picked_items = get_picked_items_qty(packed_items)
		self.validate_picked_qty(picked_items)

		picked_qty = frappe._dict()
		for d in picked_items:
			picked_qty[d.sales_order_item] = d.picked_qty

		for packed_item in packed_items:
			frappe.db.set_value(
				"Packed Item",
				packed_item,
				"picked_qty",
				flt(picked_qty.get(packed_item)),
				update_modified=False,
			)

	def update_sales_order_item_qty(self, so_items):
		picked_items = get_picked_items_qty(so_items)
		self.validate_picked_qty(picked_items)

		picked_qty = frappe._dict()
		for d in picked_items:
			picked_qty[d.sales_order_item] = d.picked_qty

		for so_item in so_items:
			frappe.db.set_value(
				"Sales Order Item",
				so_item,
				"picked_qty",
				flt(picked_qty.get(so_item)),
				update_modified=False,
			)

	def update_sales_order_picking_status(self) -> None:
		sales_orders = []
		for row in self.locations:
			if row.sales_order and row.sales_order not in sales_orders:
				sales_orders.append(row.sales_order)

		for sales_order in sales_orders:
			frappe.get_doc("Sales Order", sales_order, for_update=True).update_picking_status()

	@frappe.whitelist()
	def create_stock_reservation_entries(self, notify=True) -> None:
		"""Creates Stock Reservation Entries for Sales Order Items against Pick List."""

		so_items_details_map = {}
		for location in self.locations:
			if location.warehouse and location.sales_order and location.sales_order_item:
				item_details = {
					"sales_order_item": location.sales_order_item,
					"item_code": location.item_code,
					"warehouse": location.warehouse,
					"qty_to_reserve": (flt(location.picked_qty) - flt(location.stock_reserved_qty)),
					"from_voucher_no": location.parent,
					"from_voucher_detail_no": location.name,
					"serial_and_batch_bundle": location.serial_and_batch_bundle,
				}
				so_items_details_map.setdefault(location.sales_order, []).append(item_details)

		if so_items_details_map:
			for so, items_details in so_items_details_map.items():
				so_doc = frappe.get_doc("Sales Order", so)
				so_doc.create_stock_reservation_entries(
					items_details=items_details,
					from_voucher_type="Pick List",
					notify=notify,
				)

	@frappe.whitelist()
	def cancel_stock_reservation_entries(self, notify=True) -> None:
		"""Cancel Stock Reservation Entries for Sales Order Items created against Pick List."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)

		cancel_stock_reservation_entries(
			from_voucher_type="Pick List", from_voucher_no=self.name, notify=notify
		)

	def validate_picked_qty(self, data):
		over_delivery_receipt_allowance = 100 + flt(
			frappe.db.get_single_value("Stock Settings", "over_delivery_receipt_allowance")
		)

		for row in data:
			if (row.picked_qty / row.stock_qty) * 100 > over_delivery_receipt_allowance:
				frappe.throw(
					_(
						"You are picking more than required quantity for the item {0}. Check if there is any other pick list created for the sales order {1}."
					).format(row.item_code, row.sales_order)
				)

	@frappe.whitelist()
	def set_item_locations(self, save=False):
		self.validate_for_qty()
		items = self.aggregate_item_qty()
		picked_items_details = self.get_picked_items_details(items)
		self.item_location_map = frappe._dict()

		from_warehouses = [self.parent_warehouse] if self.parent_warehouse else []
		if self.parent_warehouse:
			from_warehouses.extend(get_descendants_of("Warehouse", self.parent_warehouse))

		# Create replica before resetting, to handle empty table on update after submit.
		locations_replica = self.get("locations")

		# reset
		self.delete_key("locations")
		updated_locations = frappe._dict()
		for item_doc in items:
			item_code = item_doc.item_code

			self.item_location_map.setdefault(
				item_code,
				get_available_item_locations(
					item_code,
					from_warehouses,
					self.item_count_map.get(item_code),
					self.company,
					picked_item_details=picked_items_details.get(item_code),
					consider_rejected_warehouses=self.consider_rejected_warehouses,
				),
			)

			locations = get_items_with_location_and_quantity(item_doc, self.item_location_map, self.docstatus)

			item_doc.idx = None
			item_doc.name = None

			for row in locations:
				location = item_doc.as_dict()
				location.update(row)
				key = (
					location.item_code,
					location.warehouse,
					location.uom,
					location.batch_no,
					location.serial_no,
					location.sales_order_item or location.material_request_item,
				)

				if key not in updated_locations:
					updated_locations.setdefault(key, location)
				else:
					updated_locations[key].qty += location.qty
					updated_locations[key].stock_qty += location.stock_qty

		for location in updated_locations.values():
			if location.picked_qty > location.stock_qty:
				location.picked_qty = location.stock_qty

			self.append("locations", location)

		# If table is empty on update after submit, set stock_qty, picked_qty to 0 so that indicator is red
		# and give feedback to the user. This is to avoid empty Pick Lists.
		if not self.get("locations") and self.docstatus == 1:
			for location in locations_replica:
				location.stock_qty = 0
				location.picked_qty = 0
				self.append("locations", location)
			frappe.msgprint(
				_(
					"Please Restock Items and Update the Pick List to continue. To discontinue, cancel the Pick List."
				),
				title=_("Out of Stock"),
				indicator="red",
			)

		if save:
			self.save()

	def aggregate_item_qty(self):
		locations = self.get("locations")
		self.item_count_map = {}
		# aggregate qty for same item
		item_map = OrderedDict()
		for item in locations:
			if not item.item_code:
				frappe.throw(f"Row #{item.idx}: Item Code is Mandatory")
			if not cint(
				frappe.get_cached_value("Item", item.item_code, "is_stock_item")
			) and not frappe.db.exists("Product Bundle", {"new_item_code": item.item_code, "disabled": 0}):
				continue
			item_code = item.item_code
			reference = item.sales_order_item or item.material_request_item
			key = (item_code, item.uom, item.warehouse, item.batch_no, reference)

			item.idx = None
			item.name = None

			if item_map.get(key):
				item_map[key].qty += item.qty
				item_map[key].stock_qty += flt(item.stock_qty, item.precision("stock_qty"))
			else:
				item_map[key] = item

			# maintain count of each item (useful to limit get query)
			self.item_count_map.setdefault(item_code, 0)
			self.item_count_map[item_code] += flt(item.stock_qty, item.precision("stock_qty"))

		return item_map.values()

	def validate_for_qty(self):
		if self.purpose == "Material Transfer for Manufacture" and (
			self.for_qty is None or self.for_qty == 0
		):
			frappe.throw(_("Qty of Finished Goods Item should be greater than 0."))

	def before_print(self, settings=None):
		if self.group_same_items:
			self.group_similar_items()

	def group_similar_items(self):
		group_item_qty = defaultdict(float)
		group_picked_qty = defaultdict(float)

		for item in self.locations:
			group_item_qty[(item.item_code, item.warehouse)] += item.qty
			group_picked_qty[(item.item_code, item.warehouse)] += item.picked_qty

		duplicate_list = []
		for item in self.locations:
			if (item.item_code, item.warehouse) in group_item_qty:
				item.qty = group_item_qty[(item.item_code, item.warehouse)]
				item.picked_qty = group_picked_qty[(item.item_code, item.warehouse)]
				item.stock_qty = group_item_qty[(item.item_code, item.warehouse)]
				del group_item_qty[(item.item_code, item.warehouse)]
			else:
				duplicate_list.append(item)

		for item in duplicate_list:
			self.remove(item)

		for idx, item in enumerate(self.locations, start=1):
			item.idx = idx

	def update_bundle_picked_qty(self):
		product_bundles = self._get_product_bundles()
		product_bundle_qty_map = self._get_product_bundle_qty_map(product_bundles.values())

		for so_row, item_code in product_bundles.items():
			picked_qty = self._compute_picked_qty_for_bundle(so_row, product_bundle_qty_map[item_code])
			item_table = "Sales Order Item"
			already_picked = frappe.db.get_value(item_table, so_row, "picked_qty", for_update=True)
			frappe.db.set_value(
				item_table,
				so_row,
				"picked_qty",
				already_picked + (picked_qty * (1 if self.docstatus == 1 else -1)),
			)

	def get_picked_items_details(self, items):
		picked_items = frappe._dict()

		if not items:
			return picked_items

		items_data = self._get_pick_list_items(items)

		for item_data in items_data:
			key = (item_data.warehouse, item_data.batch_no) if item_data.batch_no else item_data.warehouse
			serial_no = [x for x in item_data.serial_no.split("\n") if x] if item_data.serial_no else None

			if item_data.serial_and_batch_bundle:
				if not serial_no:
					serial_no = get_serial_nos_from_bundle(item_data.serial_and_batch_bundle)

				if not item_data.batch_no and not serial_no:
					bundle_batches = get_batches_from_bundle(item_data.serial_and_batch_bundle)
					for batch_no, batch_qty in bundle_batches.items():
						batch_qty = abs(batch_qty)

						key = (item_data.warehouse, batch_no)
						if item_data.item_code not in picked_items:
							picked_items[item_data.item_code] = {key: {"picked_qty": batch_qty}}
						else:
							picked_items[item_data.item_code][key]["picked_qty"] += batch_qty

					continue

			if item_data.item_code not in picked_items:
				picked_items[item_data.item_code] = {}

			if key not in picked_items[item_data.item_code]:
				picked_items[item_data.item_code][key] = frappe._dict(
					{
						"picked_qty": 0,
						"serial_no": [],
						"batch_no": item_data.batch_no or "",
						"warehouse": item_data.warehouse,
					}
				)

			picked_items[item_data.item_code][key]["picked_qty"] += item_data.picked_qty
			if serial_no:
				picked_items[item_data.item_code][key]["serial_no"].extend(serial_no)

		return picked_items

	def _get_pick_list_items(self, items):
		pi = frappe.qb.DocType("Pick List")
		pi_item = frappe.qb.DocType("Pick List Item")
		query = (
			frappe.qb.from_(pi)
			.inner_join(pi_item)
			.on(pi.name == pi_item.parent)
			.select(
				pi_item.item_code,
				pi_item.warehouse,
				pi_item.batch_no,
				pi_item.serial_and_batch_bundle,
				pi_item.serial_no,
				(Case().when(pi_item.picked_qty > 0, pi_item.picked_qty).else_(pi_item.stock_qty)).as_(
					"picked_qty"
				),
			)
			.where(
				(pi_item.item_code.isin([x.item_code for x in items]))
				& ((pi_item.picked_qty > 0) | (pi_item.stock_qty > 0))
				& (pi.status != "Completed")
				& (pi.status != "Cancelled")
				& (pi_item.docstatus != 2)
			)
		)

		if self.name:
			query = query.where(pi_item.parent != self.name)

		query = query.for_update()

		return query.run(as_dict=True)

	def _get_product_bundles(self) -> dict[str, str]:
		# Dict[so_item_row: item_code]
		product_bundles = {}
		for item in self.locations:
			if not item.product_bundle_item:
				continue
			product_bundles[item.product_bundle_item] = frappe.db.get_value(
				"Sales Order Item",
				item.product_bundle_item,
				"item_code",
			)
		return product_bundles

	def _get_product_bundle_qty_map(self, bundles: list[str]) -> dict[str, dict[str, float]]:
		# bundle_item_code: Dict[component, qty]
		product_bundle_qty_map = {}
		for bundle_item_code in bundles:
			bundle = frappe.get_last_doc("Product Bundle", {"new_item_code": bundle_item_code, "disabled": 0})
			product_bundle_qty_map[bundle_item_code] = {item.item_code: item.qty for item in bundle.items}
		return product_bundle_qty_map

	def _compute_picked_qty_for_bundle(self, bundle_row, bundle_items) -> int:
		"""Compute how many full bundles can be created from picked items."""
		precision = frappe.get_precision("Stock Ledger Entry", "qty_after_transaction")

		possible_bundles = []
		for item in self.locations:
			if item.product_bundle_item != bundle_row:
				continue

			if qty_in_bundle := bundle_items.get(item.item_code):
				possible_bundles.append(item.picked_qty / qty_in_bundle)
			else:
				possible_bundles.append(0)
		return int(flt(min(possible_bundles), precision or 6))

	def has_unreserved_stock(self):
		if self.purpose == "Delivery":
			for location in self.locations:
				if (
					location.sales_order
					and location.sales_order_item
					and (flt(location.picked_qty) - flt(location.stock_reserved_qty)) > 0
				):
					return True

		return False

	def has_reserved_stock(self):
		if self.purpose == "Delivery":
			for location in self.locations:
				if (
					location.sales_order
					and location.sales_order_item
					and flt(location.stock_reserved_qty) > 0
				):
					return True

		return False


def update_pick_list_status(pick_list):
	if pick_list:
		doc = frappe.get_doc("Pick List", pick_list)
		doc.run_method("update_status")


def get_picked_items_qty(items) -> list[dict]:
	pi_item = frappe.qb.DocType("Pick List Item")
	return (
		frappe.qb.from_(pi_item)
		.select(
			pi_item.sales_order_item,
			pi_item.item_code,
			pi_item.sales_order,
			Sum(pi_item.stock_qty).as_("stock_qty"),
			Sum(pi_item.picked_qty).as_("picked_qty"),
		)
		.where((pi_item.docstatus == 1) & (pi_item.sales_order_item.isin(items)))
		.groupby(
			pi_item.sales_order_item,
			pi_item.sales_order,
		)
		.for_update()
	).run(as_dict=True)


def validate_item_locations(pick_list):
	if not pick_list.locations:
		frappe.throw(_("Add items in the Item Locations table"))


def get_items_with_location_and_quantity(item_doc, item_location_map, docstatus):
	available_locations = item_location_map.get(item_doc.item_code)
	locations = []

	# if stock qty is zero on submitted entry, show positive remaining qty to recalculate in case of restock.
	remaining_stock_qty = item_doc.qty if (docstatus == 1 and item_doc.stock_qty == 0) else item_doc.stock_qty

	precision = frappe.get_precision("Pick List Item", "qty")
	while flt(remaining_stock_qty, precision) > 0 and available_locations:
		item_location = available_locations.pop(0)
		item_location = frappe._dict(item_location)

		stock_qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
		qty = stock_qty / (item_doc.conversion_factor or 1)

		uom_must_be_whole_number = frappe.get_cached_value("UOM", item_doc.uom, "must_be_whole_number")
		if uom_must_be_whole_number:
			qty = floor(qty)
			stock_qty = qty * item_doc.conversion_factor
			if not stock_qty:
				break

		serial_nos = None
		if item_location.serial_nos:
			serial_nos = "\n".join(item_location.serial_nos[0 : cint(stock_qty)])

		locations.append(
			frappe._dict(
				{
					"qty": qty,
					"stock_qty": stock_qty,
					"warehouse": item_location.warehouse,
					"serial_no": serial_nos,
					"batch_no": item_location.batch_no,
					"use_serial_batch_fields": 1,
				}
			)
		)

		remaining_stock_qty -= stock_qty

		qty_diff = item_location.qty - stock_qty
		# if extra quantity is available push current warehouse to available locations
		if qty_diff > 0:
			item_location.qty = qty_diff
			if item_location.serial_no:
				# set remaining serial numbers
				item_location.serial_no = item_location.serial_no[-int(qty_diff) :]
			available_locations = [item_location, *available_locations]

	# update available locations for the item
	item_location_map[item_doc.item_code] = available_locations
	return locations


def get_available_item_locations(
	item_code,
	from_warehouses,
	required_qty,
	company,
	ignore_validation=False,
	picked_item_details=None,
	consider_rejected_warehouses=False,
):
	locations = []

	has_serial_no = frappe.get_cached_value("Item", item_code, "has_serial_no")
	has_batch_no = frappe.get_cached_value("Item", item_code, "has_batch_no")

	if has_batch_no and has_serial_no:
		locations = get_available_item_locations_for_serial_and_batched_item(
			item_code,
			from_warehouses,
			required_qty,
			company,
			consider_rejected_warehouses=consider_rejected_warehouses,
		)
	elif has_serial_no:
		locations = get_available_item_locations_for_serialized_item(
			item_code,
			from_warehouses,
			company,
			consider_rejected_warehouses=consider_rejected_warehouses,
		)
	elif has_batch_no:
		locations = get_available_item_locations_for_batched_item(
			item_code,
			from_warehouses,
			consider_rejected_warehouses=consider_rejected_warehouses,
		)
	else:
		locations = get_available_item_locations_for_other_item(
			item_code,
			from_warehouses,
			company,
			consider_rejected_warehouses=consider_rejected_warehouses,
		)

	if picked_item_details:
		locations = filter_locations_by_picked_materials(locations, picked_item_details)

	if locations:
		locations = get_locations_based_on_required_qty(locations, required_qty)

	if not ignore_validation:
		validate_picked_materials(item_code, required_qty, locations, picked_item_details)

	return locations


def get_locations_based_on_required_qty(locations, required_qty):
	filtered_locations = []

	for location in locations:
		if location.qty >= required_qty:
			location.qty = required_qty
			filtered_locations.append(location)
			break

		required_qty -= location.qty
		filtered_locations.append(location)

	return filtered_locations


def validate_picked_materials(item_code, required_qty, locations, picked_item_details=None):
	for location in list(locations):
		if location["qty"] < 0:
			locations.remove(location)

	total_qty_available = sum(location.get("qty") for location in locations)
	remaining_qty = required_qty - total_qty_available

	if remaining_qty > 0:
		if picked_item_details:
			frappe.msgprint(
				_("{0} units of Item {1} is picked in another Pick List.").format(
					remaining_qty, get_link_to_form("Item", item_code)
				),
				title=_("Already Picked"),
			)

		else:
			frappe.msgprint(
				_("{0} units of Item {1} is not available in any of the warehouses.").format(
					remaining_qty, get_link_to_form("Item", item_code)
				),
				title=_("Insufficient Stock"),
			)


def filter_locations_by_picked_materials(locations, picked_item_details) -> list[dict]:
	filterd_locations = []
	precision = frappe.get_precision("Pick List Item", "qty")
	for row in locations:
		key = row.warehouse
		if row.batch_no:
			key = (row.warehouse, row.batch_no)

		picked_qty = picked_item_details.get(key, {}).get("picked_qty", 0)
		if not picked_qty:
			filterd_locations.append(row)
			continue
		if picked_qty > row.qty:
			row.qty = 0
			picked_item_details[key]["picked_qty"] -= row.qty
		else:
			row.qty -= picked_qty
			picked_item_details[key]["picked_qty"] = 0.0
			if row.serial_nos:
				row.serial_nos = list(set(row.serial_nos) - set(picked_item_details[key].get("serial_no")))

		if flt(row.qty, precision) > 0:
			filterd_locations.append(row)

	return filterd_locations


def get_available_item_locations_for_serial_and_batched_item(
	item_code,
	from_warehouses,
	required_qty,
	company,
	consider_rejected_warehouses=False,
):
	# Get batch nos by FIFO
	locations = get_available_item_locations_for_batched_item(
		item_code,
		from_warehouses,
		consider_rejected_warehouses=consider_rejected_warehouses,
	)

	if locations:
		sn = frappe.qb.DocType("Serial No")
		conditions = (sn.item_code == item_code) & (sn.company == company)

		for location in locations:
			location.qty = (
				required_qty if location.qty > required_qty else location.qty
			)  # if extra qty in batch

			serial_nos = (
				frappe.qb.from_(sn)
				.select(sn.name)
				.where(
					(conditions) & (sn.batch_no == location.batch_no) & (sn.warehouse == location.warehouse)
				)
				.orderby(sn.creation)
			).run(as_dict=True)

			serial_nos = [sn.name for sn in serial_nos]
			location.serial_nos = serial_nos
			location.qty = len(serial_nos)

	return locations


def get_available_item_locations_for_serialized_item(
	item_code,
	from_warehouses,
	company,
	consider_rejected_warehouses=False,
):
	sn = frappe.qb.DocType("Serial No")
	query = (
		frappe.qb.from_(sn)
		.select(sn.name, sn.warehouse)
		.where(sn.item_code == item_code)
		.orderby(sn.creation)
	)

	if from_warehouses:
		query = query.where(sn.warehouse.isin(from_warehouses))
	else:
		query = query.where(Coalesce(sn.warehouse, "") != "")
		query = query.where(sn.company == company)

	if not consider_rejected_warehouses:
		if rejected_warehouses := get_rejected_warehouses():
			query = query.where(sn.warehouse.notin(rejected_warehouses))

	serial_nos = query.run(as_list=True)

	warehouse_serial_nos_map = frappe._dict()
	for serial_no, warehouse in serial_nos:
		warehouse_serial_nos_map.setdefault(warehouse, []).append(serial_no)

	locations = []

	for warehouse, serial_nos in warehouse_serial_nos_map.items():
		qty = len(serial_nos)

		locations.append(
			frappe._dict(
				{
					"qty": qty,
					"warehouse": warehouse,
					"item_code": item_code,
					"serial_nos": serial_nos,
				}
			)
		)

	return locations


def get_available_item_locations_for_batched_item(
	item_code,
	from_warehouses,
	consider_rejected_warehouses=False,
):
	locations = []
	data = get_auto_batch_nos(
		frappe._dict(
			{
				"item_code": item_code,
				"warehouse": from_warehouses,
				"based_on": frappe.db.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
			}
		)
	)

	warehouse_wise_batches = frappe._dict()
	rejected_warehouses = get_rejected_warehouses()

	for d in data:
		if not consider_rejected_warehouses and rejected_warehouses and d.warehouse in rejected_warehouses:
			continue

		if d.warehouse not in warehouse_wise_batches:
			warehouse_wise_batches.setdefault(d.warehouse, defaultdict(float))

		warehouse_wise_batches[d.warehouse][d.batch_no] += d.qty

	for warehouse, batches in warehouse_wise_batches.items():
		for batch_no, qty in batches.items():
			locations.append(
				frappe._dict(
					{
						"qty": qty,
						"warehouse": warehouse,
						"item_code": item_code,
						"batch_no": batch_no,
					}
				)
			)

	return locations


def get_available_item_locations_for_other_item(
	item_code,
	from_warehouses,
	company,
	consider_rejected_warehouses=False,
):
	bin = frappe.qb.DocType("Bin")
	query = (
		frappe.qb.from_(bin)
		.select(bin.warehouse, bin.actual_qty.as_("qty"))
		.where((bin.item_code == item_code) & (bin.actual_qty > 0))
		.orderby(bin.creation)
	)

	if from_warehouses:
		query = query.where(bin.warehouse.isin(from_warehouses))
	else:
		wh = frappe.qb.DocType("Warehouse")
		query = query.from_(wh).where((bin.warehouse == wh.name) & (wh.company == company))

	if not consider_rejected_warehouses:
		if rejected_warehouses := get_rejected_warehouses():
			query = query.where(bin.warehouse.notin(rejected_warehouses))

	item_locations = query.run(as_dict=True)

	return item_locations


@frappe.whitelist()
def create_delivery_note(source_name, target_doc=None):
	pick_list = frappe.get_doc("Pick List", source_name)
	validate_item_locations(pick_list)
	sales_dict = dict()
	sales_orders = []
	delivery_note = None
	for location in pick_list.locations:
		if location.sales_order:
			sales_orders.append(
				frappe.db.get_value(
					"Sales Order", location.sales_order, ["customer", "name as sales_order"], as_dict=True
				)
			)

	group_key = lambda so: so["customer"]  # noqa
	for customer, rows in groupby(sorted(sales_orders, key=group_key), key=group_key):
		sales_dict[customer] = {row.sales_order for row in rows}

	if sales_dict:
		delivery_note = create_dn_with_so(sales_dict, pick_list)

	if not all(item.sales_order for item in pick_list.locations):
		delivery_note = create_dn_wo_so(pick_list)

	frappe.msgprint(_("Delivery Note(s) created for the Pick List"))
	return delivery_note


def create_dn_wo_so(pick_list):
	delivery_note = frappe.new_doc("Delivery Note")

	item_table_mapper_without_so = {
		"doctype": "Delivery Note Item",
		"field_map": {
			"rate": "rate",
			"name": "name",
			"parent": "",
		},
	}
	map_pl_locations(pick_list, item_table_mapper_without_so, delivery_note)
	delivery_note.insert(ignore_mandatory=True)

	return delivery_note


def create_dn_with_so(sales_dict, pick_list):
	delivery_note = None

	item_table_mapper = {
		"doctype": "Delivery Note Item",
		"field_map": {
			"rate": "rate",
			"name": "so_detail",
			"parent": "against_sales_order",
		},
		"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1,
	}

	for customer in sales_dict:
		for so in sales_dict[customer]:
			delivery_note = None
			kwargs = {"skip_item_mapping": True, "ignore_pricing_rule": pick_list.ignore_pricing_rule}
			delivery_note = create_delivery_note_from_sales_order(so, delivery_note, kwargs=kwargs)
			break
		if delivery_note:
			# map all items of all sales orders of that customer
			for so in sales_dict[customer]:
				map_pl_locations(pick_list, item_table_mapper, delivery_note, so)
			delivery_note.flags.ignore_mandatory = True
			delivery_note.insert()
			update_packed_item_details(pick_list, delivery_note)
			delivery_note.save()

	return delivery_note


def map_pl_locations(pick_list, item_mapper, delivery_note, sales_order=None):
	for location in pick_list.locations:
		if location.sales_order != sales_order or location.product_bundle_item:
			continue

		if location.sales_order_item:
			sales_order_item = frappe.get_doc("Sales Order Item", location.sales_order_item)
		else:
			sales_order_item = None

		source_doc = sales_order_item or location

		dn_item = map_child_doc(source_doc, delivery_note, item_mapper)

		if dn_item:
			dn_item.pick_list_item = location.name
			dn_item.warehouse = location.warehouse
			dn_item.qty = flt(location.picked_qty) / (flt(location.conversion_factor) or 1)
			dn_item.batch_no = location.batch_no
			dn_item.serial_no = location.serial_no
			dn_item.use_serial_batch_fields = location.use_serial_batch_fields

			update_delivery_note_item(source_doc, dn_item, delivery_note)

	add_product_bundles_to_delivery_note(pick_list, delivery_note, item_mapper)
	set_delivery_note_missing_values(delivery_note)

	delivery_note.pick_list = pick_list.name
	delivery_note.company = pick_list.company
	delivery_note.customer = frappe.get_value("Sales Order", sales_order, "customer")


def add_product_bundles_to_delivery_note(pick_list: "PickList", delivery_note, item_mapper) -> None:
	"""Add product bundles found in pick list to delivery note.

	When mapping pick list items, the bundle item itself isn't part of the
	locations. Dynamically fetch and add parent bundle item into DN."""
	product_bundles = pick_list._get_product_bundles()
	product_bundle_qty_map = pick_list._get_product_bundle_qty_map(product_bundles.values())

	for so_row, item_code in product_bundles.items():
		sales_order_item = frappe.get_doc("Sales Order Item", so_row)
		dn_bundle_item = map_child_doc(sales_order_item, delivery_note, item_mapper)
		dn_bundle_item.qty = pick_list._compute_picked_qty_for_bundle(
			so_row, product_bundle_qty_map[item_code]
		)
		update_delivery_note_item(sales_order_item, dn_bundle_item, delivery_note)


def update_packed_item_details(pick_list: "PickList", delivery_note) -> None:
	"""Update stock details on packed items table of delivery note."""

	def _find_so_row(packed_item):
		for item in delivery_note.items:
			if packed_item.parent_detail_docname == item.name:
				return item.so_detail

	def _find_pick_list_location(bundle_row, packed_item):
		if not bundle_row:
			return
		for loc in pick_list.locations:
			if loc.product_bundle_item == bundle_row and loc.item_code == packed_item.item_code:
				return loc

	for packed_item in delivery_note.packed_items:
		so_row = _find_so_row(packed_item)
		location = _find_pick_list_location(so_row, packed_item)
		if not location:
			continue
		packed_item.warehouse = location.warehouse
		packed_item.batch_no = location.batch_no
		packed_item.serial_no = location.serial_no


@frappe.whitelist()
def create_stock_entry(pick_list):
	pick_list = frappe.get_doc(json.loads(pick_list))
	validate_item_locations(pick_list)

	if stock_entry_exists(pick_list.get("name")):
		return frappe.msgprint(_("Stock Entry has been already created against this Pick List"))

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.pick_list = pick_list.get("name")
	stock_entry.purpose = pick_list.get("purpose")
	stock_entry.company = pick_list.get("company")
	stock_entry.set_stock_entry_type()

	if pick_list.get("work_order"):
		stock_entry = update_stock_entry_based_on_work_order(pick_list, stock_entry)
	elif pick_list.get("material_request"):
		stock_entry = update_stock_entry_based_on_material_request(pick_list, stock_entry)
	else:
		stock_entry = update_stock_entry_items_with_no_reference(pick_list, stock_entry)

	stock_entry.set_missing_values()

	return stock_entry.as_dict()


@frappe.whitelist()
def get_pending_work_orders(doctype, txt, searchfield, start, page_length, filters, as_dict):
	wo = frappe.qb.DocType("Work Order")
	return (
		frappe.qb.from_(wo)
		.select(wo.name, wo.company, wo.planned_start_date)
		.where(
			(wo.status.notin(["Completed", "Stopped"]))
			& (wo.qty > wo.material_transferred_for_manufacturing)
			& (wo.docstatus == 1)
			& (wo.company == filters.get("company"))
			& (wo.name.like(f"%{txt}%"))
		)
		.orderby(Case().when(Locate(txt, wo.name) > 0, Locate(txt, wo.name)).else_(99999))
		.orderby(wo.name)
		.limit(cint(page_length))
		.offset(start)
	).run(as_dict=as_dict)


@frappe.whitelist()
def target_document_exists(pick_list_name, purpose):
	if purpose == "Delivery":
		return frappe.db.exists("Delivery Note", {"pick_list": pick_list_name, "docstatus": 1})

	return stock_entry_exists(pick_list_name)


@frappe.whitelist()
def get_item_details(item_code, uom=None):
	details = frappe.db.get_value("Item", item_code, ["stock_uom", "name"], as_dict=1)
	details.uom = uom or details.stock_uom
	if uom:
		details.update(get_conversion_factor(item_code, uom))

	return details


def update_delivery_note_item(source, target, delivery_note):
	cost_center = frappe.db.get_value("Project", delivery_note.project, "cost_center")
	if not cost_center:
		cost_center = get_cost_center(source.item_code, "Item", delivery_note.company)

	if not cost_center:
		cost_center = get_cost_center(source.item_group, "Item Group", delivery_note.company)

	target.cost_center = cost_center


def get_cost_center(for_item, from_doctype, company):
	"""Returns Cost Center for Item or Item Group"""
	return frappe.db.get_value(
		"Item Default",
		fieldname=["buying_cost_center"],
		filters={"parent": for_item, "parenttype": from_doctype, "company": company},
	)


def set_delivery_note_missing_values(target):
	target.run_method("set_missing_values")
	target.run_method("set_po_nos")
	target.run_method("calculate_taxes_and_totals")


def stock_entry_exists(pick_list_name):
	return frappe.db.exists("Stock Entry", {"pick_list": pick_list_name})


def update_stock_entry_based_on_work_order(pick_list, stock_entry):
	work_order = frappe.get_doc("Work Order", pick_list.get("work_order"))

	stock_entry.work_order = work_order.name
	stock_entry.company = work_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = work_order.bom_no
	stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
	stock_entry.fg_completed_qty = pick_list.for_qty
	if work_order.bom_no:
		stock_entry.inspection_required = frappe.db.get_value("BOM", work_order.bom_no, "inspection_required")

	is_wip_warehouse_group = frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group")
	if not (is_wip_warehouse_group and work_order.skip_transfer):
		wip_warehouse = work_order.wip_warehouse
	else:
		wip_warehouse = None
	stock_entry.to_warehouse = wip_warehouse

	stock_entry.project = work_order.project

	for location in pick_list.locations:
		item = frappe._dict()
		update_common_item_properties(item, location)
		item.t_warehouse = wip_warehouse

		stock_entry.append("items", item)

	return stock_entry


def update_stock_entry_based_on_material_request(pick_list, stock_entry):
	for location in pick_list.locations:
		target_warehouse = None
		if location.material_request_item:
			target_warehouse = frappe.get_value(
				"Material Request Item", location.material_request_item, "warehouse"
			)
		item = frappe._dict()
		update_common_item_properties(item, location)
		item.t_warehouse = target_warehouse
		stock_entry.append("items", item)

	return stock_entry


def update_stock_entry_items_with_no_reference(pick_list, stock_entry):
	for location in pick_list.locations:
		item = frappe._dict()
		update_common_item_properties(item, location)

		stock_entry.append("items", item)

	return stock_entry


def update_common_item_properties(item, location):
	item.item_code = location.item_code
	item.s_warehouse = location.warehouse
	item.qty = location.picked_qty * location.conversion_factor
	item.transfer_qty = location.picked_qty
	item.uom = location.uom
	item.conversion_factor = location.conversion_factor
	item.stock_uom = location.stock_uom
	item.material_request = location.material_request
	item.serial_no = location.serial_no
	item.batch_no = location.batch_no
	item.material_request_item = location.material_request_item


def get_rejected_warehouses():
	if not hasattr(frappe.local, "rejected_warehouses"):
		frappe.local.rejected_warehouses = []

	if not frappe.local.rejected_warehouses:
		frappe.local.rejected_warehouses = frappe.get_all(
			"Warehouse", filters={"is_rejected_warehouse": 1}, pluck="name"
		)

	return frappe.local.rejected_warehouses
