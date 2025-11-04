# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Case


def execute(filters: dict | None = None):
	report = ReportData(filters)
	report.validate_filters()
	data = report.get_data()
	has_serial_no, has_batch_no = check_has_serial_no_in_data(data)
	columns = report.get_columns(has_serial_no, has_batch_no)

	return columns, data


def check_has_serial_no_in_data(data):
	has_serial_no = False
	has_batch_no = False

	for row in data:
		if row.get("serial_no"):
			has_serial_no = True
		if row.get("batch_no"):
			has_batch_no = True

		if has_serial_no and has_batch_no:
			break

	return has_serial_no, has_batch_no


class ReportData:
	def __init__(self, filters):
		self.filters = filters
		self.doctype_name = self.get_doctype()

	def validate_filters(self):
		if not self.filters.item_code and not self.filters.batches and not self.filters.serial_nos:
			frappe.throw(
				_("Please select at least one filter: Item Code, Batch, or Serial No."),
				title=_("Missing Filters"),
			)

	def get_data(self):
		result_data = []

		if self.filters.get("traceability_direction") in ["Backward", "Both"]:
			data = self.get_serial_no_batches()
			source_data = self.prepare_source_data(data)

			# Prepare source data with raw materials
			for key in source_data:
				sabb_data = source_data[key]
				if sabb_data.reference_doctype != "Stock Entry":
					continue

				self.set_backward_data(sabb_data)

			# Source data has all the details including raw materials
			self.parse_batch_details(source_data, result_data, "Backward")

		if self.filters.get("traceability_direction") in ["Forward", "Both"]:
			data = self.get_serial_no_batches()
			batch_details = frappe._dict({})
			for row in data:
				value = row.serial_no or row.batch_no
				self.set_forward_data(value, batch_details)

			self.parse_batch_details(batch_details, result_data, "Forward")

		return result_data

	def parse_batch_details(self, sabb_data_details, data, direction, indent=0):
		for key in sabb_data_details:
			sabb = sabb_data_details[key]
			row = {
				"item_code": sabb.item_code,
				"batch_no": sabb.batch_no,
				"serial_no": sabb.serial_no,
				"warehouse": sabb.warehouse,
				"qty": sabb.qty,
				"reference_doctype": sabb.reference_doctype,
				"reference_name": sabb.reference_name,
				"item_name": sabb.item_name,
				"posting_date": sabb.posting_date,
				"indent": indent,
				"direction": direction,
				"batch_expiry_date": sabb.get("batch_expiry_date"),
				"warranty_expiry_date": sabb.get("warranty_expiry_date"),
				"amc_expiry_date": sabb.get("amc_expiry_date"),
			}

			if data and indent == 0:
				data.append({})

			if direction == "Forward" and row["qty"] > 0:
				row["direction"] = "Backward"

			if sabb.reference_doctype == "Purchase Receipt":
				row["supplier"] = frappe.db.get_value(
					"Purchase Receipt",
					sabb.reference_name,
					"supplier",
				)
			elif sabb.reference_doctype == "Stock Entry":
				row["work_order"] = frappe.db.get_value(
					"Stock Entry",
					sabb.reference_name,
					"work_order",
				)
			elif sabb.reference_doctype == "Delivery Note":
				row["customer"] = frappe.db.get_value(
					"Delivery Note",
					sabb.reference_name,
					"customer",
				)

			data.append(row)

			raw_materials = sabb.get("raw_materials")
			if raw_materials:
				self.parse_batch_details(raw_materials, data, direction, indent + 1)

		return data

	def prepare_source_data(self, data):
		source_data = frappe._dict({})
		for row in data:
			key = (row.item_code, row.reference_name)

			value = row.serial_no or row.batch_no
			if value:
				key = (row.item_code, row.reference_name, value)

			if self.doctype_name == "Batch":
				sabb_details = self.get_qty_from_sabb(row)
				row.update(sabb_details)
			else:
				row.qty = 1

			if key not in source_data:
				row["raw_materials"] = frappe._dict({})
				source_data[key] = row

		return source_data

	def get_qty_from_sabb(self, row):
		sabb = frappe.qb.DocType("Serial and Batch Bundle")
		sabb_entry = frappe.qb.DocType("Serial and Batch Entry")

		query = (
			frappe.qb.from_(sabb)
			.inner_join(sabb_entry)
			.on(sabb.name == sabb_entry.parent)
			.select(
				sabb_entry.qty,
				sabb_entry.warehouse,
			)
			.where(
				(sabb_entry.batch_no == row.batch_no)
				& (sabb.voucher_type == row.reference_doctype)
				& (sabb.voucher_no == row.reference_name)
				& (sabb.is_cancelled == 0)
				& (sabb_entry.docstatus == 1)
			)
		)

		results = query.run(as_dict=True)

		return results[0] if results else {}

	def set_backward_data(self, sabb_data, qty=None):
		if qty:
			sabb_data.qty = qty

		if "raw_materials" not in sabb_data:
			sabb_data.raw_materials = frappe._dict({})

		materials = self.get_materials(sabb_data)
		for material in materials:
			# Recursive: batch has sub-components
			if material.serial_no or material.batch_no:
				key = (material.item_code, material.reference_name, material.name)
				value = material.serial_no or material.batch_no

				if key not in sabb_data.raw_materials:
					details = self.get_serial_no_batches(value)
					if not details:
						inward_data = self.get_sabb_entries(value, "Inward")
						if inward_data:
							details = inward_data[-1]

					if details:
						details.update(self.get_qty_from_sabb(details))
						sabb_data.raw_materials[key] = details

				if sabb_data.raw_materials.get(key):
					self.set_backward_data(sabb_data.raw_materials[key], material.qty)
			else:
				sub_key = (material.item_code, material.name)
				if sub_key not in sabb_data.raw_materials:
					sabb_data.raw_materials[sub_key] = frappe._dict(
						{
							"item_code": material.item_code,
							"item_name": material.item_name,
							"qty": material.qty or material.quantity,
							"warehouse": material.warehouse,
						}
					)

		return sabb_data

	def get_serial_no_batches(self, name=None):
		batches = self.filters.get("batches", [])
		serial_nos = self.filters.get("serial_nos", [])

		doctype = frappe.qb.DocType(self.doctype_name)
		query = frappe.qb.from_(doctype).select(
			doctype.reference_doctype,
			doctype.reference_name,
			doctype.item_name,
		)

		if self.doctype_name == "Batch":
			query = query.select(
				doctype.item.as_("item_code"),
				doctype.name.as_("batch_no"),
				doctype.manufacturing_date.as_("posting_date"),
				doctype.expiry_date.as_("batch_expiry_date"),
			)
		else:
			query = query.select(
				doctype.item_code,
				doctype.name.as_("serial_no"),
				doctype.posting_date,
				doctype.warranty_expiry_date,
				doctype.amc_expiry_date,
			)

		if name:
			query = query.where(doctype.name == name)
			data = query.run(as_dict=True)
			return data[0] if data else {}

		if batches:
			query = query.where(doctype.name.isin(batches))
		elif serial_nos:
			query = query.where(doctype.name.isin(serial_nos))

		if self.filters.get("item_code"):
			if self.doctype_name == "Serial No":
				query = query.where(doctype.item_code == self.filters.item_code)
			else:
				query = query.where(doctype.item == self.filters.item_code)

		return query.run(as_dict=True)

	def get_doctype(self):
		if self.filters.item_code:
			item_details = frappe.get_cached_value(
				"Item",
				self.filters.item_code,
				["has_batch_no", "has_serial_no"],
				as_dict=True,
			)

			if item_details.has_serial_no:
				return "Serial No"
			elif item_details.has_batch_no:
				return "Batch"

		elif self.filters.get("serial_nos"):
			return "Serial No"

		return "Batch"

	def get_materials(self, sabb_data):
		stock_entry = frappe.qb.DocType("Stock Entry")
		stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")
		sabb_entry = frappe.qb.DocType("Serial and Batch Entry")

		query = (
			frappe.qb.from_(stock_entry)
			.inner_join(stock_entry_detail)
			.on(stock_entry.name == stock_entry_detail.parent)
			.left_join(sabb_entry)
			.on(
				(stock_entry_detail.serial_and_batch_bundle == sabb_entry.parent)
				& (sabb_entry.docstatus == 1)
			)
			.select(
				stock_entry_detail.s_warehouse.as_("warehouse"),
				stock_entry_detail.item_code,
				stock_entry_detail.name,
				stock_entry_detail.item_name,
				stock_entry_detail.parenttype.as_("reference_doctype"),
				stock_entry.name.as_("reference_name"),
				(
					(
						stock_entry_detail.qty
						/ Case()
						.when(stock_entry.fg_completed_qty > 0, stock_entry.fg_completed_qty)
						.else_(sabb_data.qty)
					)
					* sabb_data.qty
				).as_("qty"),
				sabb_entry.batch_no,
				sabb_entry.serial_no,
				sabb_entry.qty.as_("quantity"),
			)
			.where(
				(stock_entry.docstatus == 1)
				& (stock_entry.purpose.isin(["Manufacture", "Repack"]))
				& (stock_entry.name == sabb_data.reference_name)
				& (stock_entry_detail.s_warehouse.isnotnull())
			)
		)

		return query.run(as_dict=True)

	def set_forward_data(self, value, sabb_data):
		outward_entries = self.get_sabb_entries(value)

		for row in outward_entries:
			if row.reference_doctype == "Stock Entry":
				self.process_manufacture_or_repack_entry(row, sabb_data)
			else:
				self.add_direct_outward_entry(row, sabb_data)

	def add_direct_outward_entry(self, row, batch_details):
		key = (row.item_code, row.reference_name)
		if key not in batch_details:
			row["indent"] = 0
			batch_details[key] = row

	def get_sabb_entries(self, value, type_of_transaction=None):
		if not type_of_transaction:
			type_of_transaction = "Outward"

		SABB = frappe.qb.DocType("Serial and Batch Bundle")
		SABE = frappe.qb.DocType("Serial and Batch Entry")

		query = (
			frappe.qb.from_(SABB)
			.inner_join(SABE)
			.on(SABB.name == SABE.parent)
			.select(
				SABB.voucher_type.as_("reference_doctype"),
				SABB.voucher_no.as_("reference_name"),
				SABE.batch_no,
				SABE.serial_no,
				SABE.qty,
				SABB.item_code,
				SABB.item_name,
				SABB.posting_date,
				SABB.warehouse,
			)
			.where(
				(SABB.is_cancelled == 0)
				& (SABE.docstatus == 1)
				& (SABB.type_of_transaction == type_of_transaction)
			)
			.orderby(SABB.posting_date)
			.orderby(SABB.posting_time)
		)

		query = query.where((SABE.serial_no == value) | (SABE.batch_no == value))

		return query.run(as_dict=True)

	def process_manufacture_or_repack_entry(self, row, batch_details):
		ste = frappe.db.get_value("Stock Entry", row.reference_name, ["purpose", "work_order"], as_dict=True)

		if ste and ste.purpose in ["Manufacture", "Repack"]:
			fg_item = self.get_finished_item_from_stock_entry(row.reference_name)
			if not fg_item:
				return

			key = (fg_item.item_code, row.reference_name)

			if key not in batch_details:
				serial_no, batch_no = self.get_serial_batch_no(fg_item.serial_and_batch_bundle)
				fg_item.update(
					{
						"work_order": ste.work_order,
						"posting_date": row.posting_date,
						"serial_no": serial_no,
						"batch_no": batch_no,
						"indent": 0,
						"warehouse": fg_item.warehouse,
						"raw_materials": frappe._dict({(row.item_code, row.reference_name): row}),
					}
				)
				batch_details[key] = fg_item

	def get_finished_item_from_stock_entry(self, reference_name):
		return frappe.db.get_value(
			"Stock Entry Detail",
			{"parent": reference_name, "is_finished_item": 1},
			[
				"item_code",
				"item_name",
				"serial_and_batch_bundle",
				"qty",
				"parenttype as reference_doctype",
				"parent as reference_name",
				"t_warehouse as warehouse",
			],
			as_dict=True,
		)

	def get_serial_batch_no(self, serial_and_batch_bundle):
		sabb_details = frappe.db.get_value(
			"Serial and Batch Entry",
			{"parent": serial_and_batch_bundle},
			["batch_no", "serial_no"],
			as_dict=True,
		)

		return (sabb_details.serial_no, sabb_details.batch_no) if sabb_details else (None, None)

	def get_columns(self, has_serial_no=None, has_batch_no=None):
		columns = [
			{
				"fieldname": "item_code",
				"label": _("Item Code"),
				"fieldtype": "Link",
				"options": "Item",
				"width": 180,
			},
			{
				"fieldname": "item_name",
				"label": _("Item Name"),
				"fieldtype": "Data",
				"width": 120,
			},
		]

		if has_serial_no:
			columns.append(
				{
					"fieldname": "serial_no",
					"label": _("Serial No"),
					"fieldtype": "Link",
					"options": "Serial No",
					"width": 120,
				}
			)

		if has_batch_no:
			columns.extend(
				[
					{
						"fieldname": "batch_no",
						"label": _("Batch No"),
						"fieldtype": "Link",
						"options": "Batch",
						"width": 120,
					},
					{
						"fieldname": "batch_expiry_date",
						"label": _("Batch Expiry Date"),
						"fieldtype": "Date",
						"width": 150,
					},
				]
			)

		columns.extend(
			[
				{
					"fieldname": "qty",
					"label": _("Quantity"),
					"fieldtype": "Float",
					"width": 90,
				},
				{
					"fieldname": "reference_doctype",
					"label": _("Voucher Type"),
					"fieldtype": "Data",
					"width": 130,
				},
				{
					"fieldname": "reference_name",
					"label": _("Source Document No"),
					"fieldtype": "Dynamic Link",
					"options": "reference_doctype",
					"width": 200,
				},
				{
					"fieldname": "warehouse",
					"label": _("Warehouse"),
					"fieldtype": "Link",
					"options": "Warehouse",
					"width": 120,
				},
				{
					"fieldname": "posting_date",
					"label": _("Posting Date"),
					"fieldtype": "Date",
					"width": 120,
				},
				{
					"fieldname": "work_order",
					"label": _("Work Order"),
					"fieldtype": "Link",
					"options": "Work Order",
					"width": 160,
				},
			]
		)

		if self.filters.get("traceability_direction") == "Backward":
			columns.append(
				{
					"fieldname": "supplier",
					"label": _("Supplier"),
					"fieldtype": "Link",
					"options": "Supplier",
					"width": 150,
				}
			)
		else:
			columns.append(
				{
					"fieldname": "customer",
					"label": _("Customer"),
					"fieldtype": "Link",
					"options": "Customer",
					"width": 150,
				}
			)

		if has_serial_no:
			columns.extend(
				[
					{
						"fieldname": "warranty_expiry_date",
						"label": _("Warranty Expiry (Serial)"),
						"fieldtype": "Date",
						"width": 200,
					},
					{
						"fieldname": "amc_expiry_date",
						"label": _("AMC Expiry (Serial)"),
						"fieldtype": "Date",
						"width": 160,
					},
				]
			)

		return columns
