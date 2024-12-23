# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.meta import get_field_precision
from frappe.utils import cint, flt, format_datetime, get_datetime

import erpnext
from erpnext.stock.serial_batch_bundle import get_batches_from_bundle
from erpnext.stock.serial_batch_bundle import get_serial_nos as get_serial_nos_from_bundle
from erpnext.stock.utils import get_incoming_rate, get_valuation_method


class StockOverReturnError(frappe.ValidationError):
	pass


def validate_return(doc):
	if not doc.meta.get_field("is_return") or not doc.is_return:
		return

	if doc.return_against:
		validate_return_against(doc)

		if doc.doctype in ("Sales Invoice", "Purchase Invoice") and not doc.update_stock:
			return

		validate_returned_items(doc)


def validate_return_against(doc):
	if not frappe.db.exists(doc.doctype, doc.return_against):
		frappe.throw(_("Invalid {0}: {1}").format(doc.meta.get_label("return_against"), doc.return_against))
	else:
		ref_doc = frappe.get_doc(doc.doctype, doc.return_against)

		party_type = "customer" if doc.doctype in ("Sales Invoice", "Delivery Note") else "supplier"

		if (
			ref_doc.company == doc.company
			and ref_doc.get(party_type) == doc.get(party_type)
			and ref_doc.docstatus.is_submitted()
		):
			# validate posting date time
			return_posting_datetime = "{} {}".format(doc.posting_date, doc.get("posting_time") or "00:00:00")
			ref_posting_datetime = "{} {}".format(
				ref_doc.posting_date,
				ref_doc.get("posting_time") or "00:00:00",
			)

			if get_datetime(return_posting_datetime) < get_datetime(ref_posting_datetime):
				frappe.throw(
					_("Posting timestamp must be after {0}").format(format_datetime(ref_posting_datetime))
				)

			# validate same exchange rate
			if doc.conversion_rate != ref_doc.conversion_rate:
				frappe.throw(
					_("Exchange Rate must be same as {0} {1} ({2})").format(
						doc.doctype, doc.return_against, ref_doc.conversion_rate
					)
				)

			# validate update stock
			if doc.doctype == "Sales Invoice" and doc.update_stock and not ref_doc.update_stock:
				frappe.throw(
					_("'Update Stock' can not be checked because items are not delivered via {0}").format(
						doc.return_against
					)
				)


def validate_returned_items(doc):
	valid_items = frappe._dict()

	select_fields = "item_code, qty, stock_qty, rate, parenttype, conversion_factor, name"
	if doc.doctype != "Purchase Invoice":
		select_fields += ",serial_no, batch_no"

	if doc.doctype in ["Purchase Invoice", "Purchase Receipt", "Subcontracting Receipt"]:
		select_fields += ",rejected_qty, received_qty"

	for d in frappe.db.sql(
		f"""select {select_fields} from `tab{doc.doctype} Item` where parent = %s""",
		doc.return_against,
		as_dict=1,
	):
		valid_items = get_ref_item_dict(valid_items, d)

	if doc.doctype in ("Delivery Note", "Sales Invoice"):
		for d in frappe.db.sql(
			"""select item_code, qty, serial_no, batch_no from `tabPacked Item`
			where parent = %s""",
			doc.return_against,
			as_dict=1,
		):
			valid_items = get_ref_item_dict(valid_items, d)

	already_returned_items = get_already_returned_items(doc)

	# ( not mandatory when it is Purchase Invoice or a Sales Invoice without Update Stock )
	warehouse_mandatory = not (
		(doc.doctype == "Purchase Invoice" or doc.doctype == "Sales Invoice") and not doc.update_stock
	)

	items_returned = False
	for d in doc.get("items"):
		key = d.item_code
		raise_exception = False
		if doc.doctype in ["Purchase Receipt", "Purchase Invoice", "Sales Invoice"]:
			field = frappe.scrub(doc.doctype) + "_item"
			if d.get(field):
				key = (d.item_code, d.get(field))
				raise_exception = True
		elif doc.doctype == "Delivery Note":
			key = (d.item_code, d.get("dn_detail"))

		if d.item_code and (flt(d.qty) < 0 or flt(d.get("received_qty")) < 0):
			if key not in valid_items:
				frappe.msgprint(
					_("Row # {0}: Returned Item {1} does not exist in {2} {3}").format(
						d.idx, d.item_code, doc.doctype, doc.return_against
					),
					raise_exception=raise_exception,
				)
			else:
				ref = valid_items.get(key, frappe._dict())
				validate_quantity(doc, key, d, ref, valid_items, already_returned_items)

				if (
					ref.rate
					and flt(d.rate) > ref.rate
					and doc.doctype in ("Delivery Note", "Sales Invoice")
					and get_valuation_method(ref.item_code) != "Moving Average"
				):
					frappe.throw(
						_("Row # {0}: Rate cannot be greater than the rate used in {1} {2}").format(
							d.idx, doc.doctype, doc.return_against
						)
					)

				if (
					warehouse_mandatory
					and not d.get("warehouse")
					and frappe.db.get_value("Item", d.item_code, "is_stock_item")
				):
					frappe.throw(_("Warehouse is mandatory"))

			items_returned = True

		elif d.item_name:
			items_returned = True

	if not items_returned:
		frappe.throw(_("Atleast one item should be entered with negative quantity in return document"))


def validate_quantity(doc, key, args, ref, valid_items, already_returned_items):
	fields = ["stock_qty"]
	if doc.doctype in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
		if not args.get("return_qty_from_rejected_warehouse"):
			fields.extend(["received_qty", "rejected_qty"])
		else:
			fields.extend(["received_qty"])

	already_returned_data = already_returned_items.get(key) or {}

	company_currency = erpnext.get_company_currency(doc.company)
	stock_qty_precision = get_field_precision(
		frappe.get_meta(doc.doctype + " Item").get_field("stock_qty"), company_currency
	)

	for column in fields:
		returned_qty = flt(already_returned_data.get(column, 0)) if len(already_returned_data) > 0 else 0

		if column == "stock_qty" and not args.get("return_qty_from_rejected_warehouse"):
			reference_qty = ref.get(column)
			current_stock_qty = args.get(column)
		elif args.get("return_qty_from_rejected_warehouse"):
			reference_qty = ref.get("rejected_qty") * ref.get("conversion_factor", 1.0)
			current_stock_qty = args.get(column) * args.get("conversion_factor", 1.0)
		else:
			reference_qty = ref.get(column) * ref.get("conversion_factor", 1.0)
			current_stock_qty = args.get(column) * args.get("conversion_factor", 1.0)

		max_returnable_qty = flt(reference_qty, stock_qty_precision) - returned_qty
		label = column.replace("_", " ").title()

		if reference_qty:
			if flt(args.get(column)) > 0:
				frappe.throw(_("{0} must be negative in return document").format(label))
			elif returned_qty >= reference_qty and args.get(column):
				frappe.throw(
					_("Item {0} has already been returned").format(args.item_code), StockOverReturnError
				)
			elif abs(flt(current_stock_qty, stock_qty_precision)) > max_returnable_qty:
				frappe.throw(
					_("Row # {0}: Cannot return more than {1} for Item {2}").format(
						args.idx, max_returnable_qty, args.item_code
					),
					StockOverReturnError,
				)


def get_ref_item_dict(valid_items, ref_item_row):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	key = ref_item_row.item_code
	if ref_item_row.get("name"):
		key = (ref_item_row.item_code, ref_item_row.name)

	valid_items.setdefault(
		key,
		frappe._dict(
			{
				"qty": 0,
				"rate": 0,
				"stock_qty": 0,
				"rejected_qty": 0,
				"received_qty": 0,
				"serial_no": [],
				"conversion_factor": ref_item_row.get("conversion_factor", 1),
				"batch_no": [],
			}
		),
	)
	item_dict = valid_items[key]
	item_dict["qty"] += ref_item_row.qty
	item_dict["stock_qty"] += ref_item_row.get("stock_qty", 0)
	if ref_item_row.get("rate", 0) > item_dict["rate"]:
		item_dict["rate"] = ref_item_row.get("rate", 0)

	if ref_item_row.parenttype in ["Purchase Invoice", "Purchase Receipt", "Subcontracting Receipt"]:
		item_dict["received_qty"] += ref_item_row.received_qty
		item_dict["rejected_qty"] += ref_item_row.rejected_qty

	if ref_item_row.get("serial_no"):
		item_dict["serial_no"] += get_serial_nos(ref_item_row.serial_no)

	if ref_item_row.get("batch_no"):
		item_dict["batch_no"].append(ref_item_row.batch_no)

	return valid_items


def get_already_returned_items(doc):
	column = "child.item_code, sum(abs(child.qty)) as qty, sum(abs(child.stock_qty)) as stock_qty"
	if doc.doctype in ["Purchase Invoice", "Purchase Receipt", "Subcontracting Receipt"]:
		column += """, sum(abs(child.rejected_qty) * child.conversion_factor) as rejected_qty,
			sum(abs(child.received_qty) * child.conversion_factor) as received_qty"""

	field = (
		frappe.scrub(doc.doctype) + "_item"
		if doc.doctype in ["Purchase Invoice", "Purchase Receipt", "Sales Invoice"]
		else "dn_detail"
	)
	data = frappe.db.sql(
		f"""
		select {column}, {field}
		from
			`tab{doc.doctype} Item` child, `tab{doc.doctype}` par
		where
			child.parent = par.name and par.docstatus = 1
			and par.is_return = 1 and par.return_against = %s
		group by item_code, {field}
	""",
		doc.return_against,
		as_dict=1,
	)

	items = {}

	for d in data:
		items.setdefault(
			(d.item_code, d.get(field)),
			frappe._dict(
				{
					"qty": d.get("qty"),
					"stock_qty": d.get("stock_qty"),
					"received_qty": d.get("received_qty"),
					"rejected_qty": d.get("rejected_qty"),
				}
			),
		)

	return items


def get_returned_qty_map_for_row(return_against, party, row_name, doctype):
	child_doctype = doctype + " Item"
	reference_field = "dn_detail" if doctype == "Delivery Note" else frappe.scrub(child_doctype)

	if doctype in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		party_type = "supplier"
	else:
		party_type = "customer"

	fields = [
		f"sum(abs(`tab{child_doctype}`.qty)) as qty",
	]

	if doctype != "Subcontracting Receipt":
		fields += [
			f"sum(abs(`tab{child_doctype}`.stock_qty)) as stock_qty",
		]

	if doctype in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		fields += [
			f"sum(abs(`tab{child_doctype}`.rejected_qty)) as rejected_qty",
			f"sum(abs(`tab{child_doctype}`.received_qty)) as received_qty",
		]

		if doctype == "Purchase Receipt":
			fields += [f"sum(abs(`tab{child_doctype}`.received_stock_qty)) as received_stock_qty"]

	# Used retrun against and supplier and is_retrun because there is an index added for it
	data = frappe.get_all(
		doctype,
		fields=fields,
		filters=[
			[doctype, "return_against", "=", return_against],
			[doctype, party_type, "=", party],
			[doctype, "docstatus", "=", 1],
			[doctype, "is_return", "=", 1],
			[child_doctype, reference_field, "=", row_name],
		],
	)

	return data[0]


def make_return_doc(doctype: str, source_name: str, target_doc=None, return_against_rejected_qty=False):
	from frappe.model.mapper import get_mapped_doc

	company = frappe.db.get_value("Delivery Note", source_name, "company")
	default_warehouse_for_sales_return = frappe.get_cached_value(
		"Company", company, "default_warehouse_for_sales_return"
	)

	def set_missing_values(source, target):
		doc = frappe.get_doc(target)
		doc.is_return = 1
		doc.ignore_pricing_rule = 1
		doc.pricing_rules = []
		doc.return_against = source.name
		doc.set_warehouse = ""
		if doctype == "Sales Invoice" or doctype == "POS Invoice":
			doc.is_pos = source.is_pos

			# look for Print Heading "Credit Note"
			if not doc.select_print_heading:
				doc.select_print_heading = frappe.get_cached_value("Print Heading", _("Credit Note"))

		elif doctype == "Purchase Invoice":
			# look for Print Heading "Debit Note"
			doc.select_print_heading = frappe.get_cached_value("Print Heading", _("Debit Note"))
			if source.tax_withholding_category:
				doc.set_onload("supplier_tds", source.tax_withholding_category)
		elif doctype == "Delivery Note":
			# manual additions to the return should hit the return warehous, too
			doc.set_warehouse = default_warehouse_for_sales_return

		for tax in doc.get("taxes") or []:
			if tax.charge_type == "Actual":
				tax.tax_amount = -1 * tax.tax_amount

		if doc.get("is_return"):
			if doc.doctype == "Sales Invoice" or doc.doctype == "POS Invoice":
				doc.consolidated_invoice = ""
				doc.set("payments", [])
				doc.update_billed_amount_in_delivery_note = True
				for data in source.payments:
					paid_amount = 0.00
					base_paid_amount = 0.00
					data.base_amount = flt(
						data.amount * source.conversion_rate, source.precision("base_paid_amount")
					)
					paid_amount += data.amount
					base_paid_amount += data.base_amount
					doc.append(
						"payments",
						{
							"mode_of_payment": data.mode_of_payment,
							"type": data.type,
							"amount": -1 * paid_amount,
							"base_amount": -1 * base_paid_amount,
							"account": data.account,
							"default": data.default,
						},
					)
				if doc.is_pos:
					doc.paid_amount = -1 * source.paid_amount
			elif doc.doctype == "Purchase Invoice":
				doc.paid_amount = -1 * source.paid_amount
				doc.base_paid_amount = -1 * source.base_paid_amount
				doc.payment_terms_template = ""
				doc.payment_schedule = []

		if doc.get("is_return") and hasattr(doc, "packed_items"):
			for d in doc.get("packed_items"):
				d.qty = d.qty * -1

		if doc.get("discount_amount"):
			doc.discount_amount = -1 * source.discount_amount

		if doctype == "Subcontracting Receipt":
			doc.set_warehouse = source.set_warehouse
			doc.supplier_warehouse = source.supplier_warehouse
		else:
			doc.run_method("calculate_taxes_and_totals")

	def update_serial_batch_no(source_doc, target_doc, source_parent, item_details, qty_field):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		returned_serial_nos = []
		returned_batches = frappe._dict()
		serial_and_batch_field = (
			"serial_and_batch_bundle" if qty_field == "stock_qty" else "rejected_serial_and_batch_bundle"
		)
		old_serial_no_field = "serial_no" if qty_field == "stock_qty" else "rejected_serial_no"
		old_batch_no_field = "batch_no"

		if (
			source_doc.get(serial_and_batch_field)
			or source_doc.get(old_serial_no_field)
			or source_doc.get(old_batch_no_field)
		):
			if item_details.has_serial_no:
				returned_serial_nos = get_returned_serial_nos(
					source_doc, source_parent, serial_no_field=serial_and_batch_field
				)
			else:
				returned_batches = get_returned_batches(
					source_doc, source_parent, batch_no_field=serial_and_batch_field
				)

			type_of_transaction = "Inward"
			if source_doc.get(serial_and_batch_field) and (
				frappe.db.get_value(
					"Serial and Batch Bundle", source_doc.get(serial_and_batch_field), "type_of_transaction"
				)
				== "Inward"
			):
				type_of_transaction = "Outward"
			elif source_parent.doctype in [
				"Purchase Invoice",
				"Purchase Receipt",
				"Subcontracting Receipt",
			]:
				type_of_transaction = "Outward"

			warehouse = source_doc.warehouse if qty_field == "stock_qty" else source_doc.rejected_warehouse
			if source_parent.doctype in [
				"Sales Invoice",
				"POS Invoice",
				"Delivery Note",
			] and source_parent.get("is_internal_customer"):
				type_of_transaction = "Outward"
				warehouse = source_doc.target_warehouse

			cls_obj = SerialBatchCreation(
				{
					"type_of_transaction": type_of_transaction,
					"serial_and_batch_bundle": source_doc.get(serial_and_batch_field),
					"returned_against": source_doc.name,
					"item_code": source_doc.item_code,
					"returned_serial_nos": returned_serial_nos,
					"voucher_type": source_parent.doctype,
					"do_not_submit": True,
					"warehouse": warehouse,
					"has_serial_no": item_details.has_serial_no,
					"has_batch_no": item_details.has_batch_no,
				}
			)

			serial_nos = []
			batches = frappe._dict()
			if source_doc.get(old_batch_no_field):
				batches = frappe._dict({source_doc.batch_no: source_doc.get(qty_field)})
			elif source_doc.get(old_serial_no_field):
				serial_nos = get_serial_nos(source_doc.get(old_serial_no_field))
			elif source_doc.get(serial_and_batch_field):
				if item_details.has_serial_no:
					serial_nos = get_serial_nos_from_bundle(source_doc.get(serial_and_batch_field))
				else:
					batches = get_batches_from_bundle(source_doc.get(serial_and_batch_field))

			if serial_nos:
				cls_obj.serial_nos = sorted(list(set(serial_nos) - set(returned_serial_nos)))
			elif batches:
				for batch in batches:
					if batch in returned_batches:
						batches[batch] -= flt(returned_batches.get(batch))

				cls_obj.batches = batches

			if source_doc.get(serial_and_batch_field):
				cls_obj.duplicate_package()
				if cls_obj.serial_and_batch_bundle:
					target_doc.set(serial_and_batch_field, cls_obj.serial_and_batch_bundle)
			else:
				target_doc.set(serial_and_batch_field, cls_obj.make_serial_and_batch_bundle().name)

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = -1 * source_doc.qty
		target_doc.pricing_rules = None
		if doctype in ["Purchase Receipt", "Subcontracting Receipt"]:
			returned_qty_map = get_returned_qty_map_for_row(
				source_parent.name, source_parent.supplier, source_doc.name, doctype
			)

			if doctype == "Subcontracting Receipt":
				target_doc.received_qty = -1 * flt(source_doc.qty)
			else:
				target_doc.received_qty = -1 * flt(
					source_doc.received_qty - (returned_qty_map.get("received_qty") or 0)
				)
				target_doc.rejected_qty = -1 * flt(
					source_doc.rejected_qty - (returned_qty_map.get("rejected_qty") or 0)
				)

			target_doc.qty = -1 * flt(source_doc.qty - (returned_qty_map.get("qty") or 0))

			if hasattr(target_doc, "stock_qty") and not return_against_rejected_qty:
				target_doc.stock_qty = -1 * flt(
					source_doc.stock_qty - (returned_qty_map.get("stock_qty") or 0)
				)
				target_doc.received_stock_qty = -1 * flt(
					source_doc.received_stock_qty - (returned_qty_map.get("received_stock_qty") or 0)
				)

			if doctype == "Subcontracting Receipt":
				target_doc.subcontracting_order = source_doc.subcontracting_order
				target_doc.subcontracting_order_item = source_doc.subcontracting_order_item
				target_doc.rejected_warehouse = source_doc.rejected_warehouse
				target_doc.subcontracting_receipt_item = source_doc.name
			else:
				target_doc.purchase_order = source_doc.purchase_order
				target_doc.purchase_order_item = source_doc.purchase_order_item
				target_doc.rejected_warehouse = source_doc.rejected_warehouse
				target_doc.purchase_receipt_item = source_doc.name

			if doctype == "Purchase Receipt" and return_against_rejected_qty:
				target_doc.qty = -1 * flt(source_doc.rejected_qty - (returned_qty_map.get("qty") or 0))
				target_doc.rejected_qty = 0.0
				target_doc.rejected_warehouse = ""
				target_doc.warehouse = source_doc.rejected_warehouse
				target_doc.received_qty = target_doc.qty
				target_doc.return_qty_from_rejected_warehouse = 1

		elif doctype == "Purchase Invoice":
			returned_qty_map = get_returned_qty_map_for_row(
				source_parent.name, source_parent.supplier, source_doc.name, doctype
			)
			target_doc.received_qty = -1 * flt(
				source_doc.received_qty - (returned_qty_map.get("received_qty") or 0)
			)
			target_doc.rejected_qty = -1 * flt(
				source_doc.rejected_qty - (returned_qty_map.get("rejected_qty") or 0)
			)
			target_doc.qty = -1 * flt(source_doc.qty - (returned_qty_map.get("qty") or 0))

			target_doc.stock_qty = -1 * flt(source_doc.stock_qty - (returned_qty_map.get("stock_qty") or 0))
			target_doc.purchase_order = source_doc.purchase_order
			target_doc.purchase_receipt = source_doc.purchase_receipt
			target_doc.rejected_warehouse = source_doc.rejected_warehouse
			target_doc.po_detail = source_doc.po_detail
			target_doc.pr_detail = source_doc.pr_detail
			target_doc.purchase_invoice_item = source_doc.name

		elif doctype == "Delivery Note":
			returned_qty_map = get_returned_qty_map_for_row(
				source_parent.name, source_parent.customer, source_doc.name, doctype
			)
			target_doc.qty = -1 * flt(source_doc.qty - (returned_qty_map.get("qty") or 0))
			target_doc.stock_qty = -1 * flt(source_doc.stock_qty - (returned_qty_map.get("stock_qty") or 0))

			target_doc.against_sales_order = source_doc.against_sales_order
			target_doc.against_sales_invoice = source_doc.against_sales_invoice
			target_doc.so_detail = source_doc.so_detail
			target_doc.si_detail = source_doc.si_detail
			target_doc.expense_account = source_doc.expense_account
			target_doc.dn_detail = source_doc.name
			if default_warehouse_for_sales_return:
				target_doc.warehouse = default_warehouse_for_sales_return
		elif doctype == "Sales Invoice" or doctype == "POS Invoice":
			returned_qty_map = get_returned_qty_map_for_row(
				source_parent.name, source_parent.customer, source_doc.name, doctype
			)
			target_doc.qty = -1 * flt(source_doc.qty - (returned_qty_map.get("qty") or 0))
			target_doc.stock_qty = -1 * flt(source_doc.stock_qty - (returned_qty_map.get("stock_qty") or 0))

			target_doc.sales_order = source_doc.sales_order
			target_doc.delivery_note = source_doc.delivery_note
			target_doc.so_detail = source_doc.so_detail
			target_doc.dn_detail = source_doc.dn_detail
			target_doc.expense_account = source_doc.expense_account

			if doctype == "Sales Invoice":
				target_doc.sales_invoice_item = source_doc.name
			else:
				target_doc.pos_invoice_item = source_doc.name

			if default_warehouse_for_sales_return:
				target_doc.warehouse = default_warehouse_for_sales_return

		if not source_doc.use_serial_batch_fields and source_doc.serial_and_batch_bundle:
			target_doc.serial_no = None
			target_doc.batch_no = None

		if (
			(source_doc.serial_no or source_doc.batch_no)
			and not source_doc.serial_and_batch_bundle
			and not source_doc.use_serial_batch_fields
		):
			target_doc.set("use_serial_batch_fields", 1)

		if source_doc.item_code and target_doc.get("use_serial_batch_fields"):
			item_details = frappe.get_cached_value(
				"Item", source_doc.item_code, ["has_batch_no", "has_serial_no"], as_dict=1
			)

			if not item_details.has_batch_no and not item_details.has_serial_no:
				return

			update_non_bundled_serial_nos(source_doc, target_doc, source_parent)

	def update_non_bundled_serial_nos(source_doc, target_doc, source_parent):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if source_doc.serial_no:
			returned_serial_nos = get_returned_non_bundled_serial_nos(source_doc, source_parent)
			serial_nos = list(set(get_serial_nos(source_doc.serial_no)) - set(returned_serial_nos))
			if serial_nos:
				target_doc.serial_no = "\n".join(serial_nos)

		if source_doc.get("rejected_serial_no"):
			returned_serial_nos = get_returned_non_bundled_serial_nos(
				source_doc, source_parent, serial_no_field="rejected_serial_no"
			)
			rejected_serial_nos = list(
				set(get_serial_nos(source_doc.rejected_serial_no)) - set(returned_serial_nos)
			)
			if rejected_serial_nos:
				target_doc.rejected_serial_no = "\n".join(rejected_serial_nos)

	def get_returned_non_bundled_serial_nos(child_doc, parent_doc, serial_no_field="serial_no"):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		return_ref_field = frappe.scrub(child_doc.doctype)
		if child_doc.doctype == "Delivery Note Item":
			return_ref_field = "dn_detail"

		serial_nos = []

		fields = [f"`{'tab' + child_doc.doctype}`.`{serial_no_field}`"]

		filters = [
			[parent_doc.doctype, "return_against", "=", parent_doc.name],
			[parent_doc.doctype, "is_return", "=", 1],
			[child_doc.doctype, return_ref_field, "=", child_doc.name],
			[parent_doc.doctype, "docstatus", "=", 1],
		]

		for row in frappe.get_all(parent_doc.doctype, fields=fields, filters=filters):
			serial_nos.extend(get_serial_nos(row.get(serial_no_field)))

		return serial_nos

	def update_terms(source_doc, target_doc, source_parent):
		target_doc.payment_amount = -source_doc.payment_amount

	def item_condition(doc):
		if return_against_rejected_qty:
			return doc.rejected_qty

		return doc.qty

	doclist = get_mapped_doc(
		doctype,
		source_name,
		{
			doctype: {
				"doctype": doctype,
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			doctype + " Item": {
				"doctype": doctype + " Item",
				"field_map": {"serial_no": "serial_no", "batch_no": "batch_no", "bom": "bom"},
				"postprocess": update_item,
				"condition": item_condition,
			},
			"Payment Schedule": {"doctype": "Payment Schedule", "postprocess": update_terms},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


def get_rate_for_return(
	voucher_type,
	voucher_no,
	item_code,
	return_against=None,
	item_row=None,
	voucher_detail_no=None,
	sle=None,
):
	if not return_against:
		return_against = frappe.get_cached_value(voucher_type, voucher_no, "return_against")

	return_against_item_field = get_return_against_item_fields(voucher_type)

	filters = get_filters(
		voucher_type,
		voucher_no,
		voucher_detail_no,
		return_against,
		item_code,
		return_against_item_field,
		item_row,
	)

	if voucher_type in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		select_field = "incoming_rate"
	else:
		select_field = "abs(stock_value_difference / actual_qty)"

	rate = flt(frappe.db.get_value("Stock Ledger Entry", filters, select_field))
	if not (rate and return_against) and voucher_type in ["Sales Invoice", "Delivery Note"]:
		rate = frappe.db.get_value(f"{voucher_type} Item", voucher_detail_no, "incoming_rate")

		if not rate and sle:
			rate = get_incoming_rate(
				{
					"item_code": sle.item_code,
					"warehouse": sle.warehouse,
					"posting_date": sle.get("posting_date"),
					"posting_time": sle.get("posting_time"),
					"qty": sle.actual_qty,
					"serial_and_batch_bundle": sle.get("serial_and_batch_bundle"),
					"company": sle.company,
					"voucher_type": sle.voucher_type,
					"voucher_no": sle.voucher_no,
				},
				raise_error_if_no_rate=False,
			)

	return rate


def get_return_against_item_fields(voucher_type):
	return_against_item_fields = {
		"Purchase Receipt": "purchase_receipt_item",
		"Purchase Invoice": "purchase_invoice_item",
		"Delivery Note": "dn_detail",
		"Sales Invoice": "sales_invoice_item",
		"Subcontracting Receipt": "subcontracting_receipt_item",
	}
	return return_against_item_fields[voucher_type]


def get_filters(
	voucher_type,
	voucher_no,
	voucher_detail_no,
	return_against,
	item_code,
	return_against_item_field,
	item_row,
):
	filters = {"voucher_type": voucher_type, "voucher_no": return_against, "item_code": item_code}

	if item_row:
		reference_voucher_detail_no = item_row.get(return_against_item_field)
	else:
		reference_voucher_detail_no = frappe.db.get_value(
			voucher_type + " Item", voucher_detail_no, return_against_item_field
		)

	if reference_voucher_detail_no:
		filters["voucher_detail_no"] = reference_voucher_detail_no

	if voucher_type in ["Purchase Receipt", "Purchase Invoice"] and item_row and item_row.get("warehouse"):
		filters["warehouse"] = item_row.get("warehouse")

	return filters


def get_returned_serial_nos(child_doc, parent_doc, serial_no_field=None, ignore_voucher_detail_no=None):
	from erpnext.stock.doctype.serial_no.serial_no import (
		get_serial_nos as get_serial_nos_from_serial_no,
	)
	from erpnext.stock.serial_batch_bundle import get_serial_nos

	if not serial_no_field:
		serial_no_field = "serial_and_batch_bundle"

	old_field = "serial_no"
	if serial_no_field == "rejected_serial_and_batch_bundle":
		old_field = "rejected_serial_no"

	return_ref_field = frappe.scrub(child_doc.doctype)
	if child_doc.doctype == "Delivery Note Item":
		return_ref_field = "dn_detail"

	serial_nos = []

	fields = [
		f"`{'tab' + child_doc.doctype}`.`{serial_no_field}`",
		f"`{'tab' + child_doc.doctype}`.`{old_field}`",
	]

	filters = [
		[parent_doc.doctype, "return_against", "=", parent_doc.name],
		[parent_doc.doctype, "is_return", "=", 1],
		[child_doc.doctype, return_ref_field, "=", child_doc.name],
		[parent_doc.doctype, "docstatus", "=", 1],
	]

	if serial_no_field == "rejected_serial_and_batch_bundle":
		filters.append([child_doc.doctype, "rejected_qty", ">", 0])

	# Required for POS Invoice
	if ignore_voucher_detail_no:
		filters.append([child_doc.doctype, "name", "!=", ignore_voucher_detail_no])

	ids = []
	for row in frappe.get_all(parent_doc.doctype, fields=fields, filters=filters):
		ids.append(row.get("serial_and_batch_bundle"))
		if row.get(old_field) and not row.get(serial_no_field):
			serial_nos.extend(get_serial_nos_from_serial_no(row.get(old_field)))

	if ids:
		serial_nos.extend(get_serial_nos(ids))

	return serial_nos


def get_returned_batches(child_doc, parent_doc, batch_no_field=None, ignore_voucher_detail_no=None):
	from erpnext.stock.serial_batch_bundle import get_batches_from_bundle

	batches = frappe._dict()

	old_field = "batch_no"
	if not batch_no_field:
		batch_no_field = "serial_and_batch_bundle"

	return_ref_field = frappe.scrub(child_doc.doctype)
	if child_doc.doctype == "Delivery Note Item":
		return_ref_field = "dn_detail"

	fields = [
		f"`{'tab' + child_doc.doctype}`.`{batch_no_field}`",
		f"`{'tab' + child_doc.doctype}`.`batch_no`",
		f"`{'tab' + child_doc.doctype}`.`stock_qty`",
	]

	filters = [
		[parent_doc.doctype, "return_against", "=", parent_doc.name],
		[parent_doc.doctype, "is_return", "=", 1],
		[child_doc.doctype, return_ref_field, "=", child_doc.name],
		[parent_doc.doctype, "docstatus", "=", 1],
	]

	if batch_no_field == "rejected_serial_and_batch_bundle":
		filters.append([child_doc.doctype, "rejected_qty", ">", 0])

	# Required for POS Invoice
	if ignore_voucher_detail_no:
		filters.append([child_doc.doctype, "name", "!=", ignore_voucher_detail_no])

	ids = []
	for row in frappe.get_all(parent_doc.doctype, fields=fields, filters=filters):
		ids.append(row.get("serial_and_batch_bundle"))
		if row.get(old_field) and not row.get(batch_no_field):
			batches.setdefault(row.get(old_field), row.get("stock_qty"))

	if ids:
		batches.update(get_batches_from_bundle(ids))

	return batches


def available_serial_batch_for_return(field, doctype, reference_ids, is_rejected=False):
	available_dict = get_available_serial_batches(field, doctype, reference_ids, is_rejected=is_rejected)
	if not available_dict:
		frappe.throw(_("No Serial / Batches are available for return"))

	return available_dict


def get_available_serial_batches(field, doctype, reference_ids, is_rejected=False):
	_bundle_ids = get_serial_and_batch_bundle(field, doctype, reference_ids, is_rejected=is_rejected)
	if not _bundle_ids:
		return frappe._dict({})

	return get_serial_batches_based_on_bundle(field, _bundle_ids)


def get_serial_batches_based_on_bundle(field, _bundle_ids):
	available_dict = frappe._dict({})
	batch_serial_nos = frappe.get_all(
		"Serial and Batch Bundle",
		fields=[
			"`tabSerial and Batch Entry`.`serial_no`",
			"`tabSerial and Batch Entry`.`batch_no`",
			"`tabSerial and Batch Entry`.`qty`",
			"`tabSerial and Batch Entry`.`incoming_rate`",
			"`tabSerial and Batch Bundle`.`voucher_detail_no`",
			"`tabSerial and Batch Bundle`.`voucher_type`",
			"`tabSerial and Batch Bundle`.`voucher_no`",
		],
		filters=[
			["Serial and Batch Bundle", "name", "in", _bundle_ids],
			["Serial and Batch Entry", "docstatus", "=", 1],
		],
		order_by="`tabSerial and Batch Bundle`.`creation`, `tabSerial and Batch Entry`.`idx`",
	)

	for row in batch_serial_nos:
		key = row.voucher_detail_no
		if frappe.get_cached_value(row.voucher_type, row.voucher_no, "is_return"):
			key = frappe.get_cached_value(row.voucher_type + " Item", row.voucher_detail_no, field)

		if row.voucher_type in ["Sales Invoice", "Delivery Note"]:
			row.qty = -1 * row.qty

		if key not in available_dict:
			available_dict[key] = frappe._dict(
				{
					"qty": 0.0,
					"serial_nos": defaultdict(float),
					"batches": defaultdict(float),
					"serial_nos_valuation": defaultdict(float),
					"batches_valuation": defaultdict(float),
				}
			)

		available_dict[key]["qty"] += row.qty

		if row.serial_no:
			available_dict[key]["serial_nos"][row.serial_no] += row.qty
			available_dict[key]["serial_nos_valuation"][row.serial_no] = row.incoming_rate
		elif row.batch_no:
			available_dict[key]["batches"][row.batch_no] += row.qty
			available_dict[key]["batches_valuation"][row.batch_no] = row.incoming_rate

	return available_dict


def get_serial_and_batch_bundle(field, doctype, reference_ids, is_rejected=False):
	filters = {"docstatus": 1, "name": ("in", reference_ids), "serial_and_batch_bundle": ("is", "set")}

	pluck_field = "serial_and_batch_bundle"
	if is_rejected:
		del filters["serial_and_batch_bundle"]
		filters["rejected_serial_and_batch_bundle"] = ("is", "set")
		pluck_field = "rejected_serial_and_batch_bundle"

	_bundle_ids = frappe.get_all(
		doctype,
		filters=filters,
		pluck=pluck_field,
	)

	if not _bundle_ids:
		return {}

	del filters["name"]

	filters[field] = ("in", reference_ids)

	if not is_rejected:
		_bundle_ids.extend(
			frappe.get_all(
				doctype,
				filters=filters,
				pluck="serial_and_batch_bundle",
			)
		)
	else:
		fields = ["serial_and_batch_bundle"]

		if is_rejected:
			fields.append("rejected_serial_and_batch_bundle")

			if doctype == "Purchase Receipt Item":
				fields.append("return_qty_from_rejected_warehouse")

		del filters["rejected_serial_and_batch_bundle"]
		data = frappe.get_all(
			doctype,
			fields=fields,
			filters=filters,
		)

		for d in data:
			if not d.get("serial_and_batch_bundle") and not d.get("rejected_serial_and_batch_bundle"):
				continue

			if is_rejected:
				if d.get("return_qty_from_rejected_warehouse"):
					_bundle_ids.append(d.get("serial_and_batch_bundle"))
				else:
					_bundle_ids.append(d.get("rejected_serial_and_batch_bundle"))
			else:
				_bundle_ids.append(d.get("serial_and_batch_bundle"))

	return _bundle_ids


def filter_serial_batches(parent_doc, data, row, warehouse_field=None, qty_field=None):
	if not qty_field:
		qty_field = "qty"

	if not warehouse_field:
		warehouse_field = "warehouse"

	warehouse = row.get(warehouse_field)
	qty = abs(row.get(qty_field))

	filterd_serial_batch = frappe._dict(
		{
			"serial_nos": [],
			"batches": defaultdict(float),
			"serial_nos_valuation": data.get("serial_nos_valuation"),
			"batches_valuation": data.get("batches_valuation"),
		}
	)

	if data.serial_nos:
		available_serial_nos = []
		for serial_no, sn_qty in data.serial_nos.items():
			if sn_qty != 0:
				available_serial_nos.append(serial_no)

		if available_serial_nos:
			if parent_doc.doctype in ["Purchase Invoice", "Purchase Receipt"]:
				available_serial_nos = get_available_serial_nos(available_serial_nos, warehouse)

			if len(available_serial_nos) > qty:
				filterd_serial_batch["serial_nos"] = sorted(available_serial_nos[0 : cint(qty)])
			else:
				filterd_serial_batch["serial_nos"] = available_serial_nos

	elif data.batches:
		for batch_no, batch_qty in data.batches.items():
			if parent_doc.get("is_internal_customer"):
				batch_qty = batch_qty * -1

			if batch_qty <= 0:
				continue

			if parent_doc.doctype in ["Purchase Invoice", "Purchase Receipt"]:
				batch_qty = get_available_batch_qty(
					parent_doc,
					batch_no,
					warehouse,
				)

				if batch_qty <= 0:
					frappe.throw(
						_("Batch {0} is not available in warehouse {1}").format(batch_no, warehouse),
						title=_("Batch Not Available for Return"),
					)

			if qty <= 0:
				break

			if batch_qty > qty:
				filterd_serial_batch["batches"][batch_no] = qty
				qty = 0
			else:
				filterd_serial_batch["batches"][batch_no] += batch_qty
				qty -= batch_qty

	return filterd_serial_batch


def get_available_batch_qty(parent_doc, batch_no, warehouse):
	from erpnext.stock.doctype.batch.batch import get_batch_qty

	return get_batch_qty(
		batch_no,
		warehouse,
		posting_date=parent_doc.posting_date,
		posting_time=parent_doc.posting_time,
		for_stock_levels=True,
	)


def make_serial_batch_bundle_for_return(data, child_doc, parent_doc, warehouse_field=None, qty_field=None):
	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	type_of_transaction = "Outward"
	if parent_doc.doctype in ["Sales Invoice", "Delivery Note", "POS Invoice"]:
		type_of_transaction = "Inward"

	if not warehouse_field:
		warehouse_field = "warehouse"

	if not qty_field:
		qty_field = "qty"

	warehouse = child_doc.get(warehouse_field)
	if parent_doc.get("is_internal_customer"):
		warehouse = child_doc.get("target_warehouse")
		type_of_transaction = "Outward"

	if not child_doc.get(qty_field):
		frappe.throw(
			_("For the {0}, the quantity is required to make the return entry").format(
				frappe.bold(child_doc.item_code)
			)
		)

	cls_obj = SerialBatchCreation(
		{
			"type_of_transaction": type_of_transaction,
			"item_code": child_doc.item_code,
			"warehouse": warehouse,
			"serial_nos": data.get("serial_nos"),
			"batches": data.get("batches"),
			"serial_nos_valuation": data.get("serial_nos_valuation"),
			"batches_valuation": data.get("batches_valuation"),
			"posting_date": parent_doc.posting_date,
			"posting_time": parent_doc.posting_time,
			"voucher_type": parent_doc.doctype,
			"voucher_no": parent_doc.name,
			"voucher_detail_no": child_doc.name,
			"qty": child_doc.get(qty_field),
			"company": parent_doc.company,
			"do_not_submit": True,
		}
	).make_serial_and_batch_bundle()

	return cls_obj.name


def get_available_serial_nos(serial_nos, warehouse):
	return frappe.get_all(
		"Serial No", filters={"warehouse": warehouse, "name": ("in", serial_nos)}, pluck="name"
	)
