import frappe
from frappe import _, bold
from frappe.query_builder import Case
from frappe.utils import flt, get_link_to_form

from erpnext.stock.serial_batch_bundle import get_serial_batch_list_from_item


class SubcontractingInwardController:
	def validate_subcontracting_inward(self):
		self.validate_inward_order()
		self.set_allow_zero_valuation_rate()
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
		self.validate_receive_from_customer_cancel()
		self.update_inward_order_received_items()
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
			match self.purpose:
				case "Receive from Customer":
					self.validate_material_receipt()
				case purpose if purpose in ["Return Raw Material to Customer", "Subcontracting Return"]:
					self.validate_returns()
				case "Material Transfer for Manufacture":
					self.validate_material_transfer()
				case "Manufacture":
					self.validate_manufacture()

	def validate_material_receipt(self):
		rm_item_fg_combo = []
		for item in self.items:
			if not frappe.get_cached_value("Item", item.item_code, "is_customer_provided_item"):
				frappe.throw(
					_("Row #{0}: Item {1} is not a Customer Provided Item.").format(
						item.idx,
						get_link_to_form("Item", item.item_code),
					)
				)

			if (
				item.scio_detail
				and frappe.get_cached_value(
					"Subcontracting Inward Order Received Item", item.scio_detail, "rm_item_code"
				)
				!= item.item_code
			):
				frappe.throw(
					_(
						"Row #{0}: Item {1} mismatch. Changing of item code is not permitted, add another row instead."
					).format(item.idx, get_link_to_form("Item", item.item_code))
				)

			if not item.scio_detail:  # item is additional
				if item.against_fg:
					if (item.item_code, item.against_fg) not in rm_item_fg_combo:
						rm_item_fg_combo.append((item.item_code, item.against_fg))
					else:
						frappe.throw(
							_(
								"Row #{0}: Customer Provided Item {1} against Subcontracting Inward Order Item {2} ({3}) cannot be added multiple times."
							).format(
								item.idx,
								get_link_to_form("Item", item.item_code),
								bold(item.against_fg),
								get_link_to_form(
									"Item",
									frappe.get_cached_value(
										"Subcontracting Inward Order Item", item.against_fg, "item_code"
									),
								),
							)
						)
				else:
					frappe.throw(
						_(
							"Row #{0}: Please select the Finished Good Item against which this Customer Provided Item will be used."
						).format(item.idx)
					)

	def validate_returns(self):
		for item in self.items:
			if not item.scio_detail:
				frappe.throw(
					_("Row #{0}: Item {1} is not a part of Subcontracting Inward Order {2}").format(
						item.idx,
						get_link_to_form("Item", item.item_code),
						get_link_to_form("Subcontracting Inward Order", self.subcontracting_inward_order),
					)
				)
			elif item.item_code != (
				frappe.get_cached_value(
					"Subcontracting Inward Order Received Item", item.scio_detail, "rm_item_code"
				)
				or frappe.get_cached_value("Subcontracting Inward Order Item", item.scio_detail, "item_code")
			):
				frappe.throw(
					_("Row #{0}: Item {1} mismatch. Changing of item code is not permitted.").format(
						item.idx, get_link_to_form("Item", item.item_code)
					)
				)

			if self.purpose == "Return Raw Material to Customer":
				data = frappe.get_value(
					"Subcontracting Inward Order Received Item",
					item.scio_detail,
					["received_qty", "returned_qty", "work_order_qty"],
					as_dict=True,
				)
				if data.returned_qty + item.transfer_qty > data.received_qty - data.work_order_qty:
					frappe.throw(
						_(
							"Row #{0}: Returned quantity cannot be greater than available quantity for Item {1}"
						).format(item.idx, get_link_to_form("Item", item.item_code))
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
						).format(item.idx, get_link_to_form("Item", item.item_code))
					)

	def validate_material_transfer(self):
		customer_warehouse = frappe.get_cached_value(
			"Subcontracting Inward Order", self.subcontracting_inward_order, "customer_warehouse"
		)
		item_codes = []
		for item in self.items:
			if not frappe.get_cached_value("Item", item.item_code, "is_customer_provided_item"):
				continue
			elif item.s_warehouse != customer_warehouse:
				frappe.throw(
					_("Row #{0}: For Customer Provided Item {1}, Source Warehouse must be {2}").format(
						item.idx,
						get_link_to_form("Item", item.item_code),
						get_link_to_form("Warehouse", customer_warehouse),
					)
				)
			elif item.item_code in item_codes:
				frappe.throw(
					_(
						"Row #{0}: Customer Provided Item {1} cannot be added multiple times in the Subcontracting Inward process."
					).format(
						item.idx,
						get_link_to_form("Item", item.item_code),
					)
				)
			else:
				work_order_items = frappe.get_all(
					"Work Order Item",
					{"parent": self.work_order, "docstatus": 1, "is_customer_provided_item": 1},
					["item_code", "transferred_qty", "required_qty", "stock_reserved_qty"],
				)
				wo_item_dict = frappe._dict(
					{
						wo_item.item_code: frappe._dict(
							{
								"transferred_qty": wo_item.transferred_qty,
								"required_qty": wo_item.required_qty,
								"stock_reserved_qty": wo_item.stock_reserved_qty,
							}
						)
						for wo_item in work_order_items
					}
				)
				if wo_item := wo_item_dict.get(item.item_code):
					if wo_item.transferred_qty + item.transfer_qty > max(
						wo_item.required_qty, wo_item.stock_reserved_qty
					):
						frappe.throw(
							_(
								"Row #{0}: Overconsumption of Customer Provided Item {1} against Work Order {2} is not allowed in the Subcontracting Inward process."
							).format(
								item.idx,
								get_link_to_form("Item", item.item_code),
								get_link_to_form("Work Order", self.work_order),
							)
						)
					else:
						item_codes.append(item.item_code)
				else:
					frappe.throw(
						_("Row #{0}: Customer Provided Item {1} is not a part of Work Order {2}").format(
							item.idx,
							get_link_to_form("Item", item.item_code),
							get_link_to_form("Work Order", self.work_order),
						)
					)

	def validate_manufacture(self):
		if next(item for item in self.items if item.is_finished_item).t_warehouse != (
			fg_warehouse := frappe.get_cached_value("Work Order", self.work_order, "fg_warehouse")
		):
			frappe.throw(
				_(
					"Target Warehouse for Finished Good must be same as Finished Good Warehouse {1} in Work Order {2} linked to the Subcontracting Inward Order."
				).format(
					get_link_to_form("Warehouse", fg_warehouse),
					get_link_to_form("Work Order", self.work_order),
				)
			)

		items = [
			item
			for item in self.get("items")
			if not item.is_finished_item
			and not item.is_scrap_item
			and frappe.get_cached_value("Item", item.item_code, "is_customer_provided_item")
		]

		customer_warehouse = frappe.get_cached_value(
			"Subcontracting Inward Order", self.subcontracting_inward_order, "customer_warehouse"
		)
		if frappe.get_cached_value("Work Order", self.work_order, "skip_transfer"):
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
					& (
						table.reference_name
						== frappe.get_cached_value(
							"Work Order", self.work_order, "subcontracting_inward_order_item"
						)
					)
					& (table.rm_item_code.isin([item.item_code for item in items]))
				)
			)
			rm_item_dict = frappe._dict(
				{
					d.rm_item_code: frappe._dict(
						{"name": d.name, "total_qty": d.total_qty, "qty": d.consumed_qty}
					)
					for d in query.run(as_dict=True)
				}
			)

			item_codes = []
			for item in items:
				if rm := rm_item_dict.get(item.item_code):
					if rm.qty + item.transfer_qty > rm.total_qty:
						frappe.throw(
							_(
								"Row #{0}: Customer Provided Item {1} exceeds quantity available through Subcontracting Inward Order"
							).format(item.idx, get_link_to_form("Item", item.item_code), item.transfer_qty)
						)
					elif item.s_warehouse != customer_warehouse:
						frappe.throw(
							_(
								"Row #{0}: For Customer Provided Item {1}, Source Warehouse must be {2}"
							).format(
								item.idx,
								get_link_to_form("Item", item.item_code),
								get_link_to_form("Warehouse", customer_warehouse),
							)
						)
					elif item.item_code in item_codes:
						frappe.throw(
							_(
								"Row #{0}: Customer Provided Item {1} cannot be added multiple times in the Subcontracting Inward process."
							).format(
								item.idx,
								get_link_to_form("Item", item.item_code),
							)
						)
					else:
						item_codes.append(item.item_code)
				else:
					frappe.throw(
						_(
							"Row #{0}: Customer Provided Item {1} is not a part of Subcontracting Inward Order {2}"
						).format(
							item.idx,
							get_link_to_form("Item", item.item_code),
							get_link_to_form("Subcontracting Inward Order", self.subcontracting_inward_order),
						)
					)
		else:
			work_order_items = frappe.get_all(
				"Work Order Item",
				{"parent": self.work_order, "docstatus": 1, "is_customer_provided_item": 1},
				["item_code", "transferred_qty", "consumed_qty"],
			)
			wo_item_dict = frappe._dict(
				{
					wo_item.item_code: frappe._dict(
						{"transferred_qty": wo_item.transferred_qty, "consumed_qty": wo_item.consumed_qty}
					)
					for wo_item in work_order_items
				}
			)
			item_codes = []
			for item in items:
				if wo_item := wo_item_dict.get(item.item_code):
					if wo_item.consumed_qty + item.transfer_qty > wo_item.transferred_qty:
						frappe.throw(
							_(
								"Row #{0}: Overconsumption of Customer Provided Item {1} against Work Order {2} is not allowed in the Subcontracting Inward process."
							).format(
								item.idx,
								get_link_to_form("Item", item.item_code),
								get_link_to_form("Work Order", self.work_order),
							)
						)
					elif item.item_code in item_codes:
						frappe.throw(
							_(
								"Row #{0}: Customer Provided Item {1} cannot be added multiple times in the Subcontracting Inward process."
							).format(
								item.idx,
								get_link_to_form("Item", item.item_code),
							)
						)
					else:
						item_codes.append(item.item_code)
				else:
					frappe.throw(
						_("Row #{0}: Customer Provided Item {1} is not a part of Work Order {2}").format(
							item.idx,
							get_link_to_form("Item", item.item_code),
							get_link_to_form("Work Order", self.work_order),
						)
					)

	def set_allow_zero_valuation_rate(self):
		if self.subcontracting_inward_order:
			if self.purpose in ["Subcontracting Delivery", "Subcontracting Return", "Manufacture"]:
				for item in self.items:
					if (item.is_finished_item or item.is_scrap_item) and item.valuation_rate == 0:
						item.allow_zero_valuation_rate = 1

	def validate_warehouse_(self):
		if self.subcontracting_inward_order and self.purpose in [
			"Receive from Customer",
			"Return Raw Material to Customer",
			"Material Transfer for Manufacture",
		]:
			customer_warehouse = frappe.get_cached_value(
				"Subcontracting Inward Order", self.subcontracting_inward_order, "customer_warehouse"
			)
			for item in self.items:
				if self.purpose == "Material Transfer for Manufacture" and not frappe.get_cached_value(
					"Item", item.item_code, "is_customer_provided_item"
				):
					continue

				if (item.s_warehouse or item.t_warehouse) != customer_warehouse:
					if item.t_warehouse:
						frappe.throw(
							_(
								"Row #{0}: Target Warehouse must be same as Customer Warehouse {1} from the linked Subcontracting Inward Order"
							).format(item.idx, get_link_to_form("Warehouse", customer_warehouse))
						)
					else:
						frappe.throw(
							_(
								"Row #{0}: Source Warehouse must be same as Customer Warehouse {1} from the linked Subcontracting Inward Order"
							).format(item.idx, get_link_to_form("Warehouse", customer_warehouse))
						)

	def validate_serial_batch_for_return_or_delivery(self):
		if self.subcontracting_inward_order and self.purpose in [
			"Return Raw Material to Customer",
			"Subcontracting Delivery",
			"Subcontracting Return",
		]:
			for item in self.items:
				serial_nos, batch_nos = self.get_serial_nos_and_batches_from_sres(
					item.scio_detail, only_pending=self.purpose != "Subcontracting Return"
				)
				serial_list, batch_list = get_serial_batch_list_from_item(item)

				if serial_list and (
					incorrect_serial_nos := [sn for sn in serial_list if sn not in serial_nos]
				):
					frappe.throw(
						_(
							"Row #{0}: Serial No(s) {1} are not a part of the linked Subcontracting Inward Order. Please select valid Serial No(s)."
						).format(
							item.idx,
							", ".join([get_link_to_form("Serial No", sn) for sn in incorrect_serial_nos]),
						)
					)
				if batch_list and (
					incorrect_batch_nos := [bn for bn in batch_list if bn not in list(batch_nos.keys())]
				):
					frappe.throw(
						_(
							"Row #{0}: Batch No(s) {1} is not a part of the linked Subcontracting Inward Order. Please select valid Batch No(s)."
						).format(
							item.idx,
							", ".join([get_link_to_form("Batch No", bn) for bn in incorrect_batch_nos]),
						)
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
				self.validate_delivery_on_save()
			else:
				for item in self.items:
					if not item.is_scrap_item:
						delivered_qty, returned_qty = frappe.get_value(
							"Subcontracting Inward Order Item",
							item.scio_detail,
							["delivered_qty", "returned_qty"],
						)
						if returned_qty > delivered_qty:
							frappe.throw(
								_(
									"Row #{0}: Cannot cancel this Stock Entry as returned quantity cannot be greater than delivered quantity for Item {1} in the linked Subcontracting Inward Order"
								).format(item.idx, get_link_to_form("Item", item.item_code))
							)

	def validate_delivery_on_save(self):
		allow_delivery_of_overproduced_qty = frappe.get_single_value(
			"Selling Settings", "allow_delivery_of_overproduced_qty"
		)

		for item in self.items:
			if not item.scio_detail:
				frappe.throw(
					_("Row #{0}: Item {1} is not a part of Subcontracting Inward Order {2}").format(
						item.idx,
						get_link_to_form("Item", item.item_code),
						get_link_to_form("Subcontracting Inward Order", self.subcontracting_inward_order),
					)
				)

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
					).as_("max_allowed_qty")
				)
				.where((table.name == item.scio_detail) & (table.docstatus == 1))
			)
			max_allowed_qty = query.run(pluck="max_allowed_qty")

			if max_allowed_qty:
				max_allowed_qty = max_allowed_qty[0]
			else:
				table = frappe.qb.DocType("Subcontracting Inward Order Scrap Item")
				query = (
					frappe.qb.from_(table)
					.select((table.produced_qty - table.delivered_qty).as_("max_allowed_qty"))
					.where((table.name == item.scio_detail) & (table.docstatus == 1))
				)
				max_allowed_qty = query.run(pluck="max_allowed_qty")[0]

			if item.transfer_qty > max_allowed_qty:
				frappe.throw(
					_(
						"Row #{0}: Quantity of Item {1} cannot be more than {2} {3} against Subcontracting Inward Order {4}"
					).format(
						item.idx,
						get_link_to_form("Item", item.item_code),
						bold(max_allowed_qty),
						bold(
							frappe.get_cached_value(
								"Subcontracting Inward Order Item"
								if not item.is_scrap_item
								else "Subcontracting Inward Order Scrap Item",
								item.scio_detail,
								"stock_uom",
							)
						),
						get_link_to_form("Subcontracting Inward Order", self.subcontracting_inward_order),
					)
				)

	def update_customer_provided_item_cost(self):
		if self.purpose == "Receive from Customer":
			for item in self.items:
				item.valuation_rate = 0
				item.customer_provided_item_cost = flt(
					item.basic_rate + (item.additional_cost / item.transfer_qty), item.precision("basic_rate")
				)

	def validate_receive_from_customer_cancel(self):
		if self.purpose == "Receive from Customer":
			for item in self.items:
				scio_rm_item = frappe.get_value(
					"Subcontracting Inward Order Received Item",
					item.scio_detail,
					["received_qty", "returned_qty", "work_order_qty"],
					as_dict=True,
				)
				if (
					scio_rm_item.received_qty - scio_rm_item.returned_qty - item.transfer_qty
				) < scio_rm_item.work_order_qty:
					frappe.throw(
						_("Row #{0}: Work Order exists against full or partial quantity of Item {1}").format(
							item.idx, get_link_to_form("Item", item.item_code)
						)
					)

	def validate_manufacture_entry_cancel(self):
		if self.subcontracting_inward_order and self.purpose == "Manufacture":
			fg_item_name = frappe.get_cached_value(
				"Work Order", self.work_order, "subcontracting_inward_order_item"
			)
			produced_qty, delivered_qty = frappe.get_value(
				"Subcontracting Inward Order Item", fg_item_name, ["produced_qty", "delivered_qty"]
			)
			if produced_qty < delivered_qty:
				frappe.throw(
					_(
						"Cannot cancel this Manufacturing Stock Entry as quantity of Finished Good produced cannot be less than quantity delivered in the linked Subcontracting Inward Order."
					)
				)

			for item in [item for item in self.items if not item.is_finished_item]:
				if item.is_scrap_item:
					scio_scrap_item = frappe.get_value(
						"Subcontracting Inward Order Scrap Item",
						{
							"docstatus": 1,
							"item_code": item.item_code,
							"warehouse": item.t_warehouse,
							"reference_name": fg_item_name,
						},
						["produced_qty", "delivered_qty"],
						as_dict=True,
					)
					if (
						scio_scrap_item
						and scio_scrap_item.delivered_qty > scio_scrap_item.produced_qty - item.transfer_qty
					):
						frappe.throw(
							_(
								"Row #{0}: Cannot cancel this Manufacturing Stock Entry as quantity of Scrap Item {1} produced cannot be less than quantity delivered."
							).format(item.idx, get_link_to_form("Item", item.item_code))
						)
				else:
					scio_rm_item = frappe.get_value(
						"Subcontracting Inward Order Received Item",
						{
							"docstatus": 1,
							"rm_item_code": item.item_code,
							"warehouse": item.s_warehouse,
							"is_customer_provided_item": 0,
							"is_additional_item": 1,
						},
						["consumed_qty", "billed_qty", "returned_qty"],
						as_dict=True,
					)
					if scio_rm_item and (scio_rm_item.billed_qty - scio_rm_item.returned_qty) > (
						scio_rm_item.consumed_qty - item.transfer_qty
					):
						frappe.throw(
							_(
								"Row #{0}: Cannot cancel this Manufacturing Stock Entry as billed quantity of Item {1} cannot be greater than consumed quantity."
							).format(item.idx, get_link_to_form("Item", item.item_code))
						)

	def update_inward_order_item(self):
		if self.purpose == "Manufacture" and (
			scio_item_name := frappe.get_cached_value(
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
		if self.subcontracting_inward_order:
			match self.purpose:
				case "Receive from Customer":
					self.update_inward_order_received_items_for_raw_materials_receipt()
				case "Manufacture":
					self.update_inward_order_received_items_for_manufacture()
				case "Return Raw Material to Customer":
					scio_rm_names = {
						item.scio_detail: item.transfer_qty
						if self._action == "submit"
						else -item.transfer_qty
						for item in self.items
					}
					case_expr = Case()
					table = frappe.qb.DocType("Subcontracting Inward Order Received Item")
					for scio_rm_name, qty in scio_rm_names.items():
						case_expr = case_expr.when(table.name == scio_rm_name, table.returned_qty + qty)

					frappe.qb.update(table).set(table.returned_qty, case_expr).where(
						(table.name.isin(list(scio_rm_names.keys()))) & (table.docstatus == 1)
					).run()

	def update_inward_order_received_items_for_raw_materials_receipt(self):
		data = frappe._dict()
		for item in self.items:
			if item.scio_detail:
				data[item.scio_detail] = frappe._dict(
					{"transfer_qty": item.transfer_qty, "rate": item.customer_provided_item_cost}
				)
			else:
				scio_rm = frappe.new_doc(
					"Subcontracting Inward Order Received Item",
					parent=self.subcontracting_inward_order,
					parenttype="Subcontracting Inward Order",
					parentfield="received_items",
					idx=frappe.db.count(
						"Subcontracting Inward Order Received Item",
						{"parent": self.subcontracting_inward_order},
					)
					+ 1,
					rm_item_code=item.item_code,
					stock_uom=item.stock_uom,
					warehouse=item.t_warehouse,
					received_qty=item.transfer_qty,
					consumed_qty=0,
					work_order_qty=0,
					returned_qty=0,
					rate=item.customer_provided_item_cost,
					is_customer_provided_item=True,
					is_additional_item=True,
					reference_name=item.against_fg,
					main_item_code=frappe.get_cached_value(
						"Subcontracting Inward Order Item", item.against_fg, "item_code"
					),
				)
				scio_rm.insert()
				scio_rm.submit()
				item.db_set("scio_detail", scio_rm.name)

		if data:
			result = frappe.get_all(
				"Subcontracting Inward Order Received Item",
				filters={
					"parent": self.subcontracting_inward_order,
					"name": ["in", list(data.keys())],
					"docstatus": 1,
				},
				fields=["rate", "name", "required_qty", "received_qty"],
			)

			deleted_docs = []
			table = frappe.qb.DocType("Subcontracting Inward Order Received Item")
			case_expr_qty, case_expr_rate = Case(), Case()
			for d in result:
				d.received_qty += (
					data[d.name].transfer_qty if self._action == "submit" else -data[d.name].transfer_qty
				)
				d.rate += data[d.name].rate if self._action == "submit" else -data[d.name].rate

				if not d.required_qty and not d.received_qty:
					deleted_docs.append(d.name)
					frappe.delete_doc("Subcontracting Inward Order Received Item", d.name)
				else:
					case_expr_qty = case_expr_qty.when(table.name == d.name, d.received_qty)
					case_expr_rate = case_expr_rate.when(table.name == d.name, d.rate)

			if final_list := list(set(data.keys()) - set(deleted_docs)):
				frappe.qb.update(table).set(table.received_qty, case_expr_qty).set(
					table.rate, case_expr_rate
				).where((table.name.isin(final_list)) & (table.docstatus == 1)).run()

	def update_inward_order_received_items_for_manufacture(self):
		customer_warehouse = frappe.get_cached_value(
			"Subcontracting Inward Order", self.subcontracting_inward_order, "customer_warehouse"
		)
		items = [item for item in self.items if not item.is_finished_item and not item.is_scrap_item]
		item_code_wh = frappe._dict(
			{
				(
					item.item_code,
					customer_warehouse
					if frappe.get_cached_value("Item", item.item_code, "is_customer_provided_item")
					else item.s_warehouse,
				): item.transfer_qty if self._action == "submit" else -item.transfer_qty
				for item in items
			}
		)
		item_codes, warehouses = zip(*list(item_code_wh.keys()), strict=True)

		table = frappe.qb.DocType("Subcontracting Inward Order Received Item")
		data = (
			frappe.qb.from_(table)
			.select(
				table.name,
				table.rm_item_code,
				table.is_customer_provided_item,
				table.consumed_qty,
				table.warehouse,
				table.is_additional_item,
			)
			.where(
				(table.docstatus == 1)
				& (table.rm_item_code.isin(list(set(item_codes))))
				& (
					(table.warehouse.isin(list(set(warehouses)))) | (table.warehouse.isnull())
				)  # warehouse will always be null for non additional self procured raw materials
				& (table.parent == self.subcontracting_inward_order)
				& (
					table.reference_name
					== frappe.get_cached_value(
						"Work Order", self.work_order, "subcontracting_inward_order_item"
					)
				)
			)
		)

		if data := data.run(as_dict=True):
			deleted_docs, used_item_wh = [], []
			case_expr = Case()
			for d in data:
				if not d.warehouse:
					d.warehouse = next(
						key[1]
						for key in item_code_wh.keys()
						if key[0] == d.rm_item_code and key not in used_item_wh
					)
					used_item_wh.append((d.rm_item_code, d.warehouse))

				qty = d.consumed_qty + item_code_wh[(d.rm_item_code, d.warehouse)]
				if qty or d.is_customer_provided_item or not d.is_additional_item:
					case_expr = case_expr.when((table.name == d.name), qty)
				else:
					deleted_docs.append(d.name)
					frappe.delete_doc("Subcontracting Inward Order Received Item", d.name)

			if final_list := list(set([d.name for d in data]) - set(deleted_docs)):
				frappe.qb.update(table).set(table.consumed_qty, case_expr).where(
					(table.name.isin(final_list)) & (table.docstatus == 1)
				).run()

			main_item_code = next(fg for fg in self.items if fg.is_finished_item).item_code
			for extra_item in [
				item
				for item in items
				if not frappe.get_cached_value("Item", item.item_code, "is_customer_provided_item")
				and (item.item_code, item.s_warehouse)
				not in [(d.rm_item_code, d.warehouse) for d in data if not d.is_customer_provided_item]
			]:
				doc = frappe.new_doc(
					"Subcontracting Inward Order Received Item",
					parent=self.subcontracting_inward_order,
					parenttype="Subcontracting Inward Order",
					parentfield="received_items",
					idx=frappe.db.count(
						"Subcontracting Inward Order Received Item",
						{"parent": self.subcontracting_inward_order},
					)
					+ 1,
					main_item_code=main_item_code,
					rm_item_code=extra_item.item_code,
					stock_uom=extra_item.stock_uom,
					reference_name=frappe.get_cached_value(
						"Work Order", self.work_order, "subcontracting_inward_order_item"
					),
					required_qty=0,
					consumed_qty=extra_item.transfer_qty,
					warehouse=extra_item.s_warehouse,
					is_additional_item=True,
				)
				doc.insert()
				doc.submit()

	def update_inward_order_scrap_items(self):
		if (scio := self.subcontracting_inward_order) and self.purpose == "Manufacture":
			scrap_items_list = [item for item in self.items if item.is_scrap_item]
			scrap_items = frappe._dict(
				{
					(item.item_code, item.t_warehouse): item.transfer_qty
					if self._action == "submit"
					else -item.transfer_qty
					for item in scrap_items_list
				}
			)
			if scrap_items:
				item_codes, warehouses = zip(*list(scrap_items.keys()), strict=True)
				item_codes = list(item_codes)
				warehouses = list(warehouses)

				result = frappe.get_all(
					"Subcontracting Inward Order Scrap Item",
					filters={
						"item_code": ["in", item_codes],
						"warehouse": ["in", warehouses],
						"reference_name": frappe.get_cached_value(
							"Work Order", self.work_order, "subcontracting_inward_order_item"
						),
						"docstatus": 1,
					},
					fields=["name", "item_code", "warehouse", "produced_qty"],
				)

				if result:
					scrap_item_dict = frappe._dict(
						{
							(d.item_code, d.warehouse): frappe._dict(
								{"name": d.name, "produced_qty": d.produced_qty}
							)
							for d in result
						}
					)
					deleted_docs = []
					case_expr = Case()
					table = frappe.qb.DocType("Subcontracting Inward Order Scrap Item")
					for key, value in scrap_item_dict.items():
						if self._action == "cancel" and value.produced_qty - abs(scrap_items.get(key)) == 0:
							deleted_docs.append(value.name)
							frappe.delete_doc("Subcontracting Inward Order Scrap Item", value.name)
						else:
							case_expr = case_expr.when(
								table.name == value.name, value.produced_qty + scrap_items.get(key)
							)

					if final_list := list(
						set([v.name for v in scrap_item_dict.values()]) - set(deleted_docs)
					):
						frappe.qb.update(table).set(table.produced_qty, case_expr).where(
							(table.name.isin(final_list)) & (table.docstatus == 1)
						).run()

				fg_item_code = next(fg for fg in self.items if fg.is_finished_item).item_code
				for scrap_item in [
					item
					for item in scrap_items_list
					if (item.item_code, item.t_warehouse) not in [(d.item_code, d.warehouse) for d in result]
				]:
					doc = frappe.new_doc(
						"Subcontracting Inward Order Scrap Item",
						parent=scio,
						parenttype="Subcontracting Inward Order",
						parentfield="scrap_items",
						idx=frappe.db.count("Subcontracting Inward Order Scrap Item", {"parent": scio}) + 1,
						item_code=scrap_item.item_code,
						fg_item_code=fg_item_code,
						stock_uom=scrap_item.stock_uom,
						warehouse=scrap_item.t_warehouse,
						produced_qty=scrap_item.transfer_qty,
						delivered_qty=0,
						reference_name=frappe.get_value(
							"Work Order", self.work_order, "subcontracting_inward_order_item"
						),
					)
					doc.insert()
					doc.submit()

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
				if item.scio_detail
				and (
					not frappe.db.exists("Subcontracting Inward Order Received Item", item.scio_detail)
					and not frappe.db.exists("Subcontracting Inward Order Item", item.scio_detail)
					and not frappe.db.exists("Subcontracting Inward Order Scrap Item", item.scio_detail)
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
				sre.has_serial_no = frappe.get_cached_value("Item", item.item_code, "has_serial_no")
				sre.has_batch_no = frappe.get_cached_value("Item", item.item_code, "has_batch_no")
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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_fg_reference_names(doctype, txt, searchfield, start, page_len, filters):
	return frappe.get_all(
		"Subcontracting Inward Order Item",
		limit_start=start,
		limit_page_length=page_len,
		filters={"parent": filters.get("parent"), "item_code": ("like", "%%%s%%" % txt), "docstatus": 1},
		fields=["name", "item_code", "delivery_warehouse"],
		as_list=True,
		order_by="idx",
	)
