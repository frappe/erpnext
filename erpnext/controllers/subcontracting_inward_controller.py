import frappe
from frappe import _, bold
from frappe.utils import flt

from erpnext.controllers.stock_controller import StockController
from erpnext.stock.serial_batch_bundle import get_serial_batch_list_from_item


class SubcontractingInwardController(StockController):
	def validate_subcontracting_inward(self):
		self.validate_inward_order()
		self.validate_customer_provided_item_for_inward()
		self.validate_warehouse_()
		self.validate_serial_batch_for_return_or_delivery()
		self.validate_delivery()
		self.update_customer_provided_item_cost()

	def on_submit_subcontracting_inward(self):
		self.update_inward_order_item()
		self.update_inward_order_received_items()
		self.update_inward_order_scrap_items()
		self.create_stock_reservation_entries_for_inward()
		self.update_inward_order_status()

	def on_cancel_subcontracting_inward(self):
		self.update_inward_order_item()
		self.validate_manufacture_entry_cancel()
		self.validate_delivery()
		self.update_inward_order_received_items()
		self.validate_receive_from_customer_cancel()
		self.update_inward_order_scrap_items()
		self.remove_reference_for_additional_items()
		self.update_inward_order_status()

	def validate_purpose(self):
		if self.subcontracting_inward_order and self.purpose not in [
			"Receive from Customer",
			"Return Raw Material to Customer",
			"Manufacture",
			"Subcontracting Delivery",
			"Subcontracting Return",
			"Material Transfer for Manufacture",
		]:
			self.subcontracting_inward_order = None

	def validate_inward_order(self):
		if self.subcontracting_inward_order:
			if self.purpose == "Receive from Customer":
				for item in self.items:
					if (
						item.scio_detail
						and frappe.db.get_value(
							"Subcontracting Inward Order Received Item", item.scio_detail, "rm_item_code"
						)
						!= item.item_code
					):
						frappe.throw(
							_(
								"Row #{0}: Item {1} mismatch. Changing of item code is not permitted, add another row instead."
							).format(item.idx, bold(item.item_code))
						)
			elif self.purpose in ["Return Raw Material to Customer", "Subcontracting Return"]:
				for item in self.items:
					if not item.scio_detail:
						frappe.throw(
							_("Row #{0}: Item {1} is not a part of Subcontracting Inward Order {2}").format(
								item.idx,
								bold(item.item_code),
								bold(self.subcontracting_inward_order),
							)
						)
					elif item.item_code != (
						frappe.db.get_value(
							"Subcontracting Inward Order Received Item", item.scio_detail, "rm_item_code"
						)
						or frappe.get_value("Subcontracting Inward Order Item", item.scio_detail, "item_code")
					):
						frappe.throw(
							_("Row #{0}: Item {1} mismatch. Changing of item code is not permitted.").format(
								item.idx, bold(item.item_code)
							)
						)

					if data := frappe.get_value(
						"Subcontracting Inward Order Received Item",
						item.scio_detail,
						["received_qty", "returned_qty", "work_order_qty"],
						as_dict=True,
					):
						if data.returned_qty + item.transfer_qty > data.received_qty - data.work_order_qty:
							frappe.throw(
								_(
									"Row #{0}: Returned quantity cannot be greater than available quantity for Item {1}"
								).format(item.idx, bold(item.item_code))
							)
					else:
						data = frappe.get_value(
							"Subcontracting Inward Order Item",
							item.scio_detail,
							["returned_qty", "delivered_qty"],
							as_dict=True,
						)
						if item.transfer_qty > data.delivered_qty - data.returned_qty:
							frappe.throw(
								_(
									"Row #{0}: Returned quantity cannot be greater than available quantity to return for Item {1}"
								).format(item.idx, bold(item.item_code))
							)
			elif self.purpose == "Manufacture":
				items = [
					item
					for item in self.get("items")
					if not item.is_finished_item
					and not item.is_scrap_item
					and frappe.db.get_value("Item", item.item_code, "is_customer_provided_item")
				]

				item_codes = [item.item_code for item in items]
				table = frappe.qb.DocType("Subcontracting Inward Order Received Item")
				query = (
					frappe.qb.from_(table)
					.select(
						table.rm_item_code,
						(table.received_qty - table.returned_qty).as_("total_qty"),
						table.consumed_qty,
						table.name,
					)
					.where(
						(table.docstatus == 1)
						& (table.parent == self.subcontracting_inward_order)
						& (table.main_item_code == frappe.db.get_value("BOM", self.bom_no, "item"))
					)
				)
				if item_codes:
					query = query.where(table.rm_item_code.isin(item_codes))
				result = query.run(as_dict=True)

				rm_item_dict = frappe._dict()
				for d in result:
					rm_item_dict[d.rm_item_code] = frappe._dict(
						{"name": d.name, "total_qty": d.total_qty, "qty": d.consumed_qty}
					)

				for item in items:
					if rm := rm_item_dict.get(item.item_code):
						rm.qty += item.transfer_qty
						warehouse = (
							frappe.db.get_value(
								"Subcontracting Inward Order",
								self.subcontracting_inward_order,
								"customer_warehouse",
							)
							if frappe.get_value("Work Order", self.work_order, "skip_transfer")
							else frappe.get_value("Work Order", self.work_order, "wip_warehouse")
						)
						if rm.qty > rm.total_qty:
							frappe.throw(
								_(
									"Row #{0}: Customer Provided Item {1} exceeds quantity available through Subcontracting Inward Order"
								).format(item.idx, bold(item.item_code), item.transfer_qty)
							)
						elif item.s_warehouse != warehouse:
							frappe.throw(
								_(
									"Row #{0}: For Customer Provided Item {1}, Source Warehouse must be {2}"
								).format(
									item.idx,
									bold(item.item_code),
									bold(warehouse),
								)
							)

					else:
						frappe.throw(
							_(
								"Row #{0}: Customer Provided Item {1} is not a part of Subcontracting Inward Order {2}"
							).format(
								item.idx,
								bold(item.item_code),
								bold(self.subcontracting_inward_order),
							)
						)

	def validate_customer_provided_item_for_inward(self):
		if self.subcontracting_inward_order:
			for item in self.items:
				if (
					item.is_finished_item
					or item.is_scrap_item
					or self.purpose in ["Subcontracting Delivery", "Subcontracting Return"]
				) and item.valuation_rate == 0:
					item.allow_zero_valuation_rate = 1
				elif self.purpose == "Receive from Customer" and not frappe.get_value(
					"Item", item.item_code, "is_customer_provided_item"
				):
					frappe.throw(
						_("Row #{0}: Item {1} is not a Customer Provided Item.").format(
							item.idx, bold(item.item_code)
						)
					)

	def validate_warehouse_(self):
		if self.subcontracting_inward_order:
			if self.purpose in [
				"Receive from Customer",
				"Return Raw Material to Customer",
				"Material Transfer for Manufacture",
			]:
				customer_warehouse = frappe.get_value(
					"Subcontracting Inward Order", self.subcontracting_inward_order, "customer_warehouse"
				)
				for item in self.items:
					if self.purpose == "Material Transfer for Manufacture" and not frappe.get_value(
						"Item", item.item_code, "is_customer_provided_item"
					):
						continue
					if (item.s_warehouse or item.t_warehouse) != customer_warehouse:
						if item.t_warehouse:
							frappe.throw(
								_(
									"Row #{0}: Target Warehouse must be same as Customer Warehouse {1} from the linked Subcontracting Inward Order"
								).format(item.idx, bold(customer_warehouse))
							)
						else:
							frappe.throw(
								_(
									"Row #{0}: Source Warehouse must be same as Customer Warehouse {1} from the linked Subcontracting Inward Order"
								).format(item.idx, bold(customer_warehouse))
							)

	def validate_serial_batch_for_return_or_delivery(self):
		if self.purpose in [
			"Return Raw Material to Customer",
			"Subcontracting Delivery",
			"Subcontracting Return",
		]:
			for item in self.items:
				serial_nos, batch_nos = self.get_serial_nos_and_batches_from_sres(
					item.scio_detail, only_pending=self.purpose != "Subcontracting Return"
				)
				serial_list, batch_list = get_serial_batch_list_from_item(item)

				if serial_list:
					for serial_no in serial_list:
						if serial_no not in serial_nos:
							frappe.throw(
								_(
									"Row #{0}: Serial No {1} is not a part of the linked Subcontracting Inward Order. Please select valid Serial No."
								).format(item.idx, bold(serial_no))
							)
				if batch_list:
					for batch_no in batch_list:
						if batch_no not in batch_nos:
							frappe.throw(
								_(
									"Row #{0}: Batch No {1} is not a part of the linked Subcontracting Inward Order. Please select valid Batch No."
								).format(item.idx, bold(batch_no))
							)

	def get_serial_nos_and_batches_from_sres(self, scio_detail, only_pending=True):
		serial_nos, batch_nos = [], frappe._dict()

		table = frappe.qb.DocType("Stock Reservation Entry")
		child_table = frappe.qb.DocType("Serial and Batch Entry")
		query = (
			frappe.qb.from_(table)
			.join(child_table)
			.on(table.name == child_table.parent)
			.select(child_table.serial_no, child_table.batch_no, child_table.qty)
			.where((table.docstatus == 1) & (table.voucher_detail_no == scio_detail))
		)

		if only_pending:
			query = query.where(child_table.qty != child_table.delivered_qty)
		else:
			query = query.where(child_table.delivered_qty > 0)

		for d in query.run(as_dict=True):
			if d.serial_no and d.serial_no not in serial_nos:
				serial_nos.append(d.serial_no)
			if d.batch_no and d.batch_no not in batch_nos:
				batch_nos[d.batch_no] = d.qty

		return serial_nos, batch_nos

	def validate_delivery(self):
		if self.purpose == "Subcontracting Delivery":
			if self._action in ["save", "submit"]:
				for item in self.items:
					if not item.scio_detail:
						frappe.throw(
							_("Row #{0}: Item {1} is not a part of Subcontracting Inward Order {2}").format(
								item.idx,
								bold(item.item_code),
								bold(self.subcontracting_inward_order),
							)
						)

					allow_delivery_of_overproduced_qty = frappe.get_single_value(
						"Selling Settings", "allow_delivery_of_overproduced_qty"
					)

					from frappe.query_builder import Case
					from pypika.terms import ValueWrapper

					table = frappe.qb.DocType("Subcontracting Inward Order Item")
					query = (
						frappe.qb.from_(table)
						.select(
							(
								Case()
								.when(
									(table.produced_qty < table.qty)
									| ValueWrapper(allow_delivery_of_overproduced_qty),
									table.produced_qty,
								)
								.else_(table.qty)
								- table.delivered_qty
								- table.returned_qty
							).as_("max_allowed_qty")
						)
						.where(table.name == item.scio_detail)
					)
					max_allowed_qty = query.run(pluck="max_allowed_qty")

					if max_allowed_qty:
						max_allowed_qty = max_allowed_qty[0]
					else:
						table = frappe.qb.DocType("Subcontracting Inward Order Scrap Item")
						query = (
							frappe.qb.from_(table)
							.select((table.produced_qty - table.delivered_qty).as_("max_allowed_qty"))
							.where(table.name == item.scio_detail)
						)
						max_allowed_qty = query.run(pluck="max_allowed_qty")[0]

					if item.transfer_qty > max_allowed_qty:
						frappe.throw(
							_(
								"Row #{0}: Quantity of Item {1} cannot be more than {2} {3} against Subcontracting Inward Order {4}"
							).format(
								item.idx,
								bold(item.item_code),
								bold(max_allowed_qty),
								bold(
									frappe.get_value(
										"Subcontracting Inward Order Item"
										if not item.is_scrap_item
										else "Subcontracting Inward Order Scrap Item",
										item.scio_detail,
										"stock_uom",
									)
								),
								bold(self.subcontracting_inward_order),
							)
						)
			else:
				for item in self.items:
					delivered_qty, returned_qty = frappe.get_value(
						"Subcontracting Inward Order Item",
						item.scio_detail,
						["delivered_qty", "returned_qty"],
					)
					if returned_qty > delivered_qty:
						frappe.throw(
							_(
								"Row #{0}: Cannot cancel this Stock Entry as returned quantity cannot be greater than delivered quantity for Item {1} in the linked Subcontracting Inward Order"
							).format(item.idx, bold(item.item_code))
						)

	def update_customer_provided_item_cost(self):
		if self.purpose == "Receive from Customer":
			for item in self.items:
				item.valuation_rate = 0
				item.customer_provided_item_cost = flt(
					item.basic_rate + (item.additional_cost / item.transfer_qty), item.precision("basic_rate")
				)

	def update_sre_for_subcontracting_delivery(self) -> None:
		"""Updates Delivered Qty in Stock Reservation Entries."""

		if self.purpose == "Subcontracting Delivery":
			if self._action == "submit":
				for item in self.get("items"):
					table = frappe.qb.DocType("Stock Reservation Entry")
					query = (
						frappe.qb.from_(table)
						.select(table.name)
						.where(
							(table.docstatus == 1)
							& (table.voucher_type == "Subcontracting Inward Order")
							& (table.voucher_no == self.subcontracting_inward_order)
							& (table.voucher_detail_no == item.scio_detail)
							& (table.warehouse == item.s_warehouse)
						)
						.orderby(table.creation)
					)
					sre_list = query.run(pluck="name")

					# Skip if no Stock Reservation Entries.
					if not sre_list:
						continue

					qty_to_deliver = item.transfer_qty
					for sre in sre_list:
						if qty_to_deliver <= 0:
							break

						sre_doc = frappe.get_doc("Stock Reservation Entry", sre)

						qty_can_be_deliver = 0
						if sre_doc.reservation_based_on == "Serial and Batch":
							sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
							if sre_doc.has_serial_no:
								delivered_serial_nos = [d.serial_no for d in sbb.entries]
								for entry in sre_doc.sb_entries:
									if entry.serial_no in delivered_serial_nos:
										entry.delivered_qty = 1  # Qty will always be 0 or 1 for Serial No.
										entry.db_update()
										qty_can_be_deliver += 1
										delivered_serial_nos.remove(entry.serial_no)
							else:
								delivered_batch_qty = {d.batch_no: -1 * d.qty for d in sbb.entries}
								for entry in sre_doc.sb_entries:
									if entry.batch_no in delivered_batch_qty:
										delivered_qty = min(
											(entry.qty - entry.delivered_qty),
											delivered_batch_qty[entry.batch_no],
										)
										entry.delivered_qty += delivered_qty
										entry.db_update()
										qty_can_be_deliver += delivered_qty
										delivered_batch_qty[entry.batch_no] -= delivered_qty
						else:
							# `Delivered Qty` should be less than or equal to `Reserved Qty`.
							qty_can_be_deliver = min(
								(sre_doc.reserved_qty - sre_doc.delivered_qty), qty_to_deliver
							)

						sre_doc.delivered_qty += qty_can_be_deliver
						sre_doc.db_update()

						# Update Stock Reservation Entry `Status` based on `Delivered Qty`.
						sre_doc.update_status()

						# Update Reserved Stock in Bin.
						sre_doc.update_reserved_stock_in_bin()

						qty_to_deliver -= qty_can_be_deliver

			if self._action == "cancel":
				for item in self.get("items"):
					table = frappe.qb.DocType("Stock Reservation Entry")
					query = (
						frappe.qb.from_(table)
						.select(table.name)
						.where(
							(table.docstatus == 1)
							& (table.voucher_type == "Subcontracting Inward Order")
							& (table.voucher_no == self.subcontracting_inward_order)
							& (table.voucher_detail_no == item.scio_detail)
							& (table.warehouse == item.s_warehouse)
						)
						.orderby(table.creation)
					)
					sre_list = query.run(pluck="name")

					# Skip if no Stock Reservation Entries.
					if not sre_list:
						continue

					qty_to_undelivered = item.transfer_qty
					for sre in sre_list:
						if qty_to_undelivered <= 0:
							break

						sre_doc = frappe.get_doc("Stock Reservation Entry", sre)

						qty_can_be_undelivered = 0
						if sre_doc.reservation_based_on == "Serial and Batch":
							sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
							if sre_doc.has_serial_no:
								serial_nos_to_undelivered = [d.serial_no for d in sbb.entries]
								for entry in sre_doc.sb_entries:
									if entry.serial_no in serial_nos_to_undelivered:
										entry.delivered_qty = 0  # Qty will always be 0 or 1 for Serial No.
										entry.db_update()
										qty_can_be_undelivered += 1
										serial_nos_to_undelivered.remove(entry.serial_no)
							else:
								batch_qty_to_undelivered = {d.batch_no: -1 * d.qty for d in sbb.entries}
								for entry in sre_doc.sb_entries:
									if entry.batch_no in batch_qty_to_undelivered:
										undelivered_qty = min(
											entry.delivered_qty, batch_qty_to_undelivered[entry.batch_no]
										)
										entry.delivered_qty -= undelivered_qty
										entry.db_update()
										qty_can_be_undelivered += undelivered_qty
										batch_qty_to_undelivered[entry.batch_no] -= undelivered_qty
						else:
							# `Qty to Undelivered` should be less than or equal to `Delivered Qty`.
							qty_can_be_undelivered = min(sre_doc.delivered_qty, qty_to_undelivered)

						sre_doc.delivered_qty -= qty_can_be_undelivered
						sre_doc.db_update()

						# Update Stock Reservation Entry `Status` based on `Delivered Qty`.
						sre_doc.update_status()

						# Update Reserved Stock in Bin.
						sre_doc.update_reserved_stock_in_bin()

						qty_to_undelivered -= qty_can_be_undelivered

	def validate_receive_from_customer_cancel(self):
		if self.purpose == "Receive from Customer":
			for item in self.items:
				scio_rm_item = frappe.get_value(
					"Subcontracting Inward Order Received Item",
					item.scio_detail,
					["received_qty", "returned_qty", "work_order_qty"],
					as_dict=True,
				)
				if (scio_rm_item.received_qty - scio_rm_item.returned_qty) < scio_rm_item.work_order_qty:
					frappe.throw(
						_("Row #{0}: Work Order exists against full or partial quantity of Item {1}").format(
							item.idx, bold(item.item_code)
						)
					)

	def validate_manufacture_entry_cancel(self):
		if self.subcontracting_inward_order and self.purpose == "Manufacture":
			fg_item_name = frappe.get_value("Work Order", self.work_order, "subcontracting_inward_order_item")
			produced_qty, delivered_qty = frappe.get_value(
				"Subcontracting Inward Order Item", fg_item_name, ["produced_qty", "delivered_qty"]
			)
			if produced_qty < delivered_qty:
				frappe.throw(
					_(
						"Cannot cancel this Manufacturing Stock Entry as quantity of Finished Good produced cannot be less than quantity delivered in the linked Subcontracting Inward Order"
					)
				)

	def update_inward_order_item(self):
		if self.purpose == "Manufacture" and (
			scio_item_name := frappe.db.get_value(
				"Work Order", self.work_order, "subcontracting_inward_order_item"
			)
		):
			if scio_item_name:
				frappe.get_doc(
					"Subcontracting Inward Order Item", scio_item_name
				).update_manufacturing_qty_fields()
		elif self.purpose in ["Subcontracting Delivery", "Subcontracting Return"]:
			fieldname = "delivered_qty" if self.purpose == "Subcontracting Delivery" else "returned_qty"
			for item in self.items:
				doctype = (
					"Subcontracting Inward Order Item"
					if not item.is_scrap_item
					else "Subcontracting Inward Order Scrap Item"
				)
				frappe.db.set_value(
					doctype,
					item.scio_detail,
					fieldname,
					frappe.get_value(doctype, item.scio_detail, fieldname)
					+ (item.transfer_qty if self._action == "submit" else -item.transfer_qty),
				)

	def update_inward_order_received_items(self):
		"""Update received items in Subcontracting Inward Order"""
		if scio := self.get("subcontracting_inward_order"):
			if self.purpose == "Receive from Customer":
				for item in self.items:
					if item.scio_detail:
						scio_rm = frappe.get_doc(
							"Subcontracting Inward Order Received Item", item.scio_detail
						)
						scio_rm.db_set(
							"received_qty",
							scio_rm.received_qty
							+ (item.transfer_qty if self._action == "submit" else -item.transfer_qty),
						)

						if not scio_rm.required_qty and not scio_rm.received_qty:
							frappe.delete_doc("Subcontracting Inward Order Received Item", scio_rm.name)
					else:
						scio_rm = frappe.new_doc(
							"Subcontracting Inward Order Received Item",
							parent=scio,
							parenttype="Subcontracting Inward Order",
							parentfield="received_items",
							idx=frappe.db.count(
								"Subcontracting Inward Order Received Item", {"parent": scio, "docstatus": 1}
							)
							+ 1,
							rm_item_code=item.item_code,
							stock_uom=item.stock_uom,
							reserve_warehouse=item.t_warehouse,
							received_qty=item.transfer_qty,
							consumed_qty=0,
							work_order_qty=0,
							returned_qty=0,
						)
						scio_rm.insert()
						scio_rm.save()
						item.db_set("scio_detail", scio_rm.name)
			elif self.purpose == "Manufacture":
				scio = frappe.get_doc("Subcontracting Inward Order", scio)
				for item in [item for item in self.items if item.s_warehouse]:
					scio_rm = next(
						(rm for rm in scio.received_items if item.item_code == rm.rm_item_code), None
					)
					if scio_rm:
						qty = scio_rm.consumed_qty + (
							item.transfer_qty if self._action == "submit" else -item.transfer_qty
						)
						if qty or scio_rm.is_customer_provided_item:
							scio_rm.db_set("consumed_qty", qty)
						elif not scio_rm.required_qty:
							frappe.delete_doc("Subcontracting Inward Order Received Item", scio_rm.name)
					else:
						doc = frappe.new_doc(
							"Subcontracting Inward Order Received Item",
							parent_doc=scio,
							parentfield="received_items",
						)
						doc.idx = len(scio.received_items) + 1
						doc.main_item_code = next(fg for fg in self.items if fg.is_finished_item).item_code
						doc.rm_item_code = item.item_code
						doc.stock_uom = item.stock_uom
						doc.reference_name = frappe.get_value(
							"Work Order", self.work_order, "subcontracting_inward_order_item"
						)
						doc.required_qty = 0
						doc.consumed_qty = item.transfer_qty
						doc.is_additional_item = True
						doc.insert()
						doc.save()
			elif self.purpose == "Return Raw Material to Customer":
				for item in self.items:
					scio_rm = frappe.get_doc("Subcontracting Inward Order Received Item", item.scio_detail)
					scio_rm.db_set(
						"returned_qty",
						scio_rm.returned_qty
						+ (item.transfer_qty if self._action == "submit" else -item.transfer_qty),
					)

	def update_inward_order_scrap_items(self):
		if (scio := self.subcontracting_inward_order) and self.purpose == "Manufacture":
			scrap_items = [item for item in self.items if item.is_scrap_item]
			if scrap_items:
				scio_doc = frappe.get_doc("Subcontracting Inward Order", scio)
				for scrap_item in scrap_items:
					if scrap_item_name := frappe.get_value(
						"Subcontracting Inward Order Scrap Item",
						filters={
							"item_code": scrap_item.item_code,
							"reference_name": frappe.get_value(
								"Work Order", self.work_order, "subcontracting_inward_order_item"
							),
						},
						fieldname="name",
					):
						scrap_item_doc = frappe.get_doc(
							"Subcontracting Inward Order Scrap Item", scrap_item_name
						)
						if (
							self._action == "cancel"
							and scrap_item_doc.produced_qty - scrap_item.transfer_qty == 0
						):
							frappe.delete_doc("Subcontracting Inward Order Scrap Item", scrap_item_doc.name)
						else:
							scrap_item_doc.db_set(
								"produced_qty",
								scrap_item_doc.produced_qty + scrap_item.transfer_qty
								if self._action == "submit"
								else -scrap_item.transfer_qty,
							)
					else:
						scrap_item_doc = frappe.new_doc(
							"Subcontracting Inward Order Scrap Item",
							parent_doc=scio_doc,
							parentfield="scrap_items",
						)
						scrap_item_doc.item_code = scrap_item.item_code
						scrap_item_doc.fg_item_code = frappe.get_value(
							"Work Order", self.work_order, "production_item"
						)
						scrap_item_doc.stock_uom = scrap_item.stock_uom
						scrap_item_doc.warehouse = scrap_item.t_warehouse
						scrap_item_doc.produced_qty = scrap_item.transfer_qty
						scrap_item_doc.delivered_qty = 0
						scrap_item_doc.reference_name = frappe.get_value(
							"Work Order", self.work_order, "subcontracting_inward_order_item"
						)
						scrap_item_doc.insert()

	def cancel_stock_reservation_entries_for_inward(self):
		if self.purpose == "Receive from Customer":
			table = frappe.qb.DocType("Stock Reservation Entry")
			query = (
				frappe.qb.from_(table)
				.select(table.name)
				.where(
					(table.docstatus == 1)
					& (table.voucher_detail_no.isin([item.scio_detail for item in self.items]))
				)
			)
			for sre in query.run(pluck="name"):
				frappe.get_doc("Stock Reservation Entry", sre).cancel()

	def remove_reference_for_additional_items(self):
		if self.subcontracting_inward_order:
			items = [
				item
				for item in self.items
				if (
					not frappe.db.exists("Subcontracting Inward Order Received Item", item.scio_detail)
					and not frappe.db.exists("Subcontracting Inward Order Item", item.scio_detail)
				)
			]
			for item in items:
				item.db_set("scio_detail", None)

	def create_stock_reservation_entries_for_inward(self):
		if self.purpose == "Receive from Customer":
			for item in self.items:
				item.reload()
				sre = frappe.new_doc("Stock Reservation Entry")
				sre.company = self.company
				sre.voucher_type = "Subcontracting Inward Order"
				sre.voucher_qty = sre.reserved_qty = sre.available_qty = item.transfer_qty
				sre.voucher_no = self.subcontracting_inward_order
				sre.voucher_detail_no = item.scio_detail
				sre.item_code = item.item_code
				sre.stock_uom = item.stock_uom
				sre.warehouse = item.t_warehouse or item.s_warehouse
				sre.has_serial_no = frappe.get_value("Item", item.item_code, "has_serial_no")
				sre.has_batch_no = frappe.get_value("Item", item.item_code, "has_batch_no")
				sre.reservation_based_on = "Qty" if not item.serial_and_batch_bundle else "Serial and Batch"
				if item.serial_and_batch_bundle:
					sabb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
					for entry in sabb.entries:
						sre.append(
							"sb_entries",
							{
								"serial_no": entry.serial_no,
								"batch_no": entry.batch_no,
								"qty": entry.qty,
								"warehouse": entry.warehouse,
							},
						)
				sre.submit()
			frappe.msgprint(_("Stock Reservation Entries Created"), alert=True, indicator="green")

	def adjust_stock_reservation_entries_for_return(self):
		if self.purpose == "Return Raw Material to Customer":
			for item in self.items:
				serial_list, batch_list = get_serial_batch_list_from_item(item)

				if serial_list or batch_list:
					table = frappe.qb.DocType("Stock Reservation Entry")
					child_table = frappe.qb.DocType("Serial and Batch Entry")
					query = (
						frappe.qb.from_(table)
						.join(child_table)
						.on(table.name == child_table.parent)
						.select(
							table.name.as_("sre_name"),
							child_table.name.as_("sbe_name"),
							child_table.batch_no,
							child_table.qty,
						)
						.where((table.docstatus == 1) & (table.voucher_detail_no == item.scio_detail))
					)
					if serial_list:
						query = query.where(child_table.serial_no.isin(serial_list))
					if batch_list:
						query = query.where(child_table.batch_no.isin(batch_list))
					result = query.run(as_dict=True)

					qty_to_deliver = {row.sre_name: 0 for row in result}
					consumed_qty = {batch: 0 for batch in batch_list}
					for row in result:
						if serial_list:
							frappe.get_doc("Serial and Batch Entry", row.sbe_name).db_set(
								"delivered_qty", 1 if self._action == "submit" else 0
							)
							qty_to_deliver[row.sre_name] += row.qty
						elif batch_list and not serial_list:
							sabe_qty = abs(
								frappe.get_value(
									"Serial and Batch Entry",
									{"parent": item.serial_and_batch_bundle, "batch_no": row.batch_no},
									"qty",
								)
							)

							qty = min(row.qty, sabe_qty)
							sbe_doc = frappe.get_doc("Serial and Batch Entry", row.sbe_name)
							sbe_doc.db_set(
								"delivered_qty",
								sbe_doc.delivered_qty + (qty if self._action == "submit" else -qty),
							)
							qty_to_deliver[row.sre_name] += qty
							consumed_qty[row.batch_no] += qty

					for sre_name, qty in qty_to_deliver.items():
						sre_doc = frappe.get_doc("Stock Reservation Entry", sre_name)
						sre_doc.db_set(
							"delivered_qty",
							sre_doc.delivered_qty + (qty if self._action == "submit" else -qty),
						)
						sre_doc.update_status()
						sre_doc.update_reserved_stock_in_bin()
				else:
					table = frappe.qb.DocType("Stock Reservation Entry")
					query = (
						frappe.qb.from_(table)
						.select(
							table.name,
							(table.reserved_qty - table.delivered_qty).as_("qty"),
						)
						.where(
							(table.docstatus == 1)
							& (table.voucher_detail_no == item.scio_detail)
							& (table.delivered_qty < table.reserved_qty)
						)
						.orderby(table.creation)
					)
					sre_list = query.run(as_dict=True)

					voucher_qty = item.transfer_qty
					for sre in sre_list:
						qty = min(sre.qty, voucher_qty)
						sre_doc = frappe.get_doc("Stock Reservation Entry", sre.name)
						sre_doc.db_set(
							"delivered_qty",
							sre_doc.delivered_qty + (qty if self._action == "submit" else -qty),
						)
						sre_doc.update_status()
						sre_doc.update_reserved_stock_in_bin()
						voucher_qty -= qty
						if voucher_qty <= 0:
							break

	def update_inward_order_status(self):
		if self.subcontracting_inward_order:
			from erpnext.subcontracting.doctype.subcontracting_inward_order.subcontracting_inward_order import (
				update_subcontracting_inward_order_status,
			)

			update_subcontracting_inward_order_status(self.subcontracting_inward_order)
