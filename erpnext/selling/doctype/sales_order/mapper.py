# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, cint, flt, nowdate, strip_html

from erpnext.accounts.party import CROSS_PARTY_FIELD_NO_MAP, get_party_account
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
	get_sales_orders,
)
from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.packed_item.packed_item import is_product_bundle, make_packing_list
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	get_sre_details_for_voucher,
	get_sre_reserved_qty_details_for_voucher,
	get_ssb_bundle_for_voucher,
)
from erpnext.stock.get_item_details import ItemDetailsCtx, get_bin_details, get_price_list_rate


def get_requested_item_qty(sales_order: str) -> dict:
	result = {}

	so = frappe.get_doc("Sales Order", sales_order)

	for item in so.items:
		if is_product_bundle(item.item_code):
			for packed_item in so.get("packed_items"):
				if (
					packed_item.parent_item == item.item_code
					and packed_item.parent_detail_docname == item.name
				):
					result[packed_item.name] = frappe._dict({"qty": packed_item.requested_qty})
		else:
			result[item.name] = frappe._dict({"qty": item.requested_qty})

	return result


@frappe.whitelist()
def make_material_request(source_name: str, target_doc: str | Document | None = None):
	requested_item_qty = get_requested_item_qty(source_name)

	def postprocess(source, target):
		if source.tc_name and frappe.db.get_value("Terms and Conditions", source.tc_name, "buying") != 1:
			target.tc_name = None
			target.terms = None

	def get_remaining_qty(so_item):
		return flt(
			flt(so_item.qty)
			- flt(requested_item_qty.get(so_item.name, {}).get("qty"))
			- max(
				flt(so_item.get("delivered_qty")),
				0,
			)
		)

	def get_remaining_packed_item_qty(so_item):
		delivered_qty = frappe.db.get_value(
			"Sales Order Item", {"name": so_item.parent_detail_docname}, ["delivered_qty"]
		)

		bundle_name = get_active_product_bundle(so_item.parent_item)
		bundle_item_qty = (
			frappe.db.get_value(
				"Product Bundle Item",
				{"parent": bundle_name, "item_code": so_item.item_code},
				["qty"],
			)
			if bundle_name
			else None
		)

		return flt(
			flt(so_item.qty)
			- flt(requested_item_qty.get(so_item.name, {}).get("qty"))
			- max(
				flt(delivered_qty) * flt(bundle_item_qty),
				0,
			)
		)

	def update_item(source, target, source_parent):
		# qty is for packed items, because packed items don't have stock_qty field
		target.project = source_parent.project
		target.qty = (
			get_remaining_packed_item_qty(source)
			if source.parentfield == "packed_items"
			else get_remaining_qty(source)
		)
		target.stock_qty = flt(target.qty) * flt(target.conversion_factor)
		target.actual_qty = get_bin_details(
			target.item_code, target.warehouse, source_parent.company, True
		).get("actual_qty", 0)

		ctx = ItemDetailsCtx(target.as_dict().copy())
		ctx.update(
			{
				"company": source_parent.get("company"),
				"price_list": frappe.db.get_single_value("Buying Settings", "buying_price_list"),
				"currency": source_parent.get("currency"),
				"conversion_rate": source_parent.get("conversion_rate"),
			}
		)

		target.rate = flt(
			get_price_list_rate(ctx, item_doc=frappe.get_cached_doc("Item", target.item_code)).get(
				"price_list_rate"
			)
		)
		target.amount = target.qty * target.rate

	doc = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {"doctype": "Material Request", "validation": {"docstatus": ["=", 1]}},
			"Packed Item": {
				"doctype": "Material Request Item",
				"field_map": {"parent": "sales_order", "uom": "stock_uom", "name": "packed_item"},
				"condition": lambda item: get_remaining_packed_item_qty(item) > 0,
				"postprocess": update_item,
			},
			"Sales Order Item": {
				"doctype": "Material Request Item",
				"field_map": {
					"name": "sales_order_item",
					"parent": "sales_order",
					"delivery_date": "schedule_date",
					"bom_no": "bom_no",
				},
				"condition": lambda item: not is_product_bundle(item.item_code)
				and get_remaining_qty(item) > 0,
				"postprocess": update_item,
			},
		},
		target_doc,
		postprocess,
	)
	if doc and doc.items:
		return doc
	else:
		frappe.throw(_("Material Request already created for the ordered quantity"))


@frappe.whitelist()
def make_project(source_name: str, target_doc: str | Document | None = None):
	def postprocess(source, doc):
		doc.project_type = "External"
		doc.project_name = source.name

	doc = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Project",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {
					"name": "sales_order",
					"base_grand_total": "estimated_costing",
					"net_total": "total_sales_amount",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doc


def set_serial_batch_for_bundle_reservation(source, target, use_serial_batch_fields, packed_sre):
	for item in source.packed_items:
		target_item = next(
			(
				d
				for d in target.packed_items
				if (d.parent_item, d.item_code, d.warehouse)
				== (item.parent_item, item.item_code, item.warehouse)
			),
			None,
		)
		if target_item and (sre := [sre for sre in packed_sre if sre.voucher_detail_no == item.name]):
			if sre[0].reservation_based_on == "Serial and Batch":
				qty = 0
				serial_nos = []
				batch_nos = []
				if use_serial_batch_fields:
					target_item.use_serial_batch_fields = 1
					for item in sre:
						qty += item.reserved_qty
						if item.has_serial_no:
							serial_nos.extend(
								frappe.get_all(
									"Serial and Batch Entry",
									filters={"parent": item.name},
									pluck="serial_no",
								)
							)
						if item.has_batch_no:
							batch_nos.extend(
								frappe.get_all(
									"Serial and Batch Entry",
									filters={"parent": item.name},
									pluck="batch_no",
								)
							)

					if len(batch_nos) == 1:
						target_item.batch_no = batch_nos[0] if batch_nos else None
					if serial_nos and len(batch_nos) < 2:
						target_item.serial_no = "\n".join(serial_nos)

				if not use_serial_batch_fields or len(batch_nos) > 1:
					target_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre).name


@frappe.whitelist()
def make_delivery_note(
	source_name: str, target_doc: str | Document | None = None, kwargs: dict | None = None
):
	if not kwargs:
		kwargs = {
			"for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
			"skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
		}

	kwargs = frappe._dict(kwargs)

	sre_details = {}
	if kwargs.for_reserved_stock:
		sre_details = get_sre_reserved_qty_details_for_voucher("Sales Order", source_name)

	mapper = {
		"Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
		"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
		"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
	}

	# 0 qty is accepted, as the qty is uncertain for some items
	has_unit_price_items = frappe.db.get_value("Sales Order", source_name, "has_unit_price_items")
	use_serial_batch_fields = frappe.get_single_value("Stock Settings", "use_serial_batch_fields")

	def is_unit_price_row(source):
		return has_unit_price_items and source.qty == 0

	def select_item(d):
		filtered_items = kwargs.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	def set_missing_values(source, target):
		if kwargs.get("ignore_pricing_rule"):
			# Skip pricing rule when the dn is creating from the pick list
			target.ignore_pricing_rule = 1

		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

		# if invoked in bulk creation, validations are ignored and thus this method is nerver invoked
		if frappe.flags.bulk_transaction:
			# set target items names to ensure proper linking with packed_items
			target.set_new_name()

		make_packing_list(target)

	def condition(doc):
		if doc.name in sre_details:
			del sre_details[doc.name]
			return False

		# make_mapped_doc sets js `args` into `frappe.flags.args`
		if frappe.flags.args and frappe.flags.args.delivery_dates:
			if frappe.utils.cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
				return False
		if frappe.flags.args and frappe.flags.args.until_delivery_date:
			if frappe.utils.cstr(doc.delivery_date) > frappe.flags.args.until_delivery_date:
				return False

		return (
			(abs(doc.delivered_qty) < abs(doc.qty)) or is_unit_price_row(doc)
		) and doc.delivered_by_supplier != 1

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = (
			flt(source.qty) if is_unit_price_row(source) else flt(source.qty) - flt(source.delivered_qty)
		)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = (
				frappe.db.get_value("Project", source_parent.project, "cost_center")
				or item.get("buying_cost_center")
				or item_group.get("buying_cost_center")
			)

	if not kwargs.skip_item_mapping:
		mapper["Sales Order Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"condition": lambda d: condition(d) and select_item(d),
			"postprocess": update_item,
		}

	so = frappe.get_doc("Sales Order", source_name)
	target_doc = get_mapped_doc("Sales Order", so.name, mapper, target_doc)

	packed_sre = []
	if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
		sre_list = get_sre_details_for_voucher("Sales Order", source_name)

		if sre_list:

			def update_dn_item(source, target, source_parent):
				update_item(source, target, so)

			so_items = {d.name: d for d in so.items if d.stock_reserved_qty}

			for sre in sre_list:
				if not so_items.get(sre.voucher_detail_no):
					packed_sre.append(sre)
					continue

				if not condition(so_items[sre.voucher_detail_no]):
					continue

				dn_item = get_mapped_doc(
					"Sales Order Item",
					sre.voucher_detail_no,
					{
						"Sales Order Item": {
							"doctype": "Delivery Note Item",
							"field_map": {
								"rate": "rate",
								"name": "so_detail",
								"parent": "against_sales_order",
							},
							"postprocess": update_dn_item,
						}
					},
					ignore_permissions=True,
				)

				dn_item.qty = flt(sre.reserved_qty) / flt(dn_item.get("conversion_factor", 1))
				dn_item.warehouse = sre.warehouse

				if (
					not use_serial_batch_fields
					and sre.reservation_based_on == "Serial and Batch"
					and (sre.has_serial_no or sre.has_batch_no)
				):
					dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher([sre]).name

				target_doc.append("items", dn_item)
			# Correct rows index.
			for idx, item in enumerate(target_doc.items):
				item.idx = idx + 1

	if not kwargs.skip_item_mapping and frappe.flags.bulk_transaction and not target_doc.items:
		# the (date) condition filter resulted in an unintendedly created empty DN; remove it
		del target_doc
		return

	# Should be called after mapping items.
	target_doc.packed_items = []
	set_missing_values(so, target_doc)
	set_serial_batch_for_bundle_reservation(so, target_doc, use_serial_batch_fields, packed_sre)

	return target_doc


@frappe.whitelist()
def make_sales_invoice(
	source_name: str,
	target_doc: str | Document | None = None,
	ignore_permissions: bool = False,
	args: str | dict | None = None,
):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	# 0 qty is accepted, as the qty is uncertain for some items
	has_unit_price_items = frappe.db.get_value("Sales Order", source_name, "has_unit_price_items")

	def is_unit_price_row(source):
		return has_unit_price_items and source.qty == 0

	def postprocess(source, target):
		set_missing_values(source, target)
		# Get the advance paid Journal Entries in Sales Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

		make_packing_list(target)
		set_serial_batch_for_bundle_reservation(
			source,
			target,
			frappe.get_single_value("Stock Settings", "use_serial_batch_fields"),
			get_sre_details_for_voucher("Sales Order", source_name),
		)

	def set_missing_values(source, target):
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

		# set the redeem loyalty points if provided via shopping cart
		if source.loyalty_points and source.order_type == "Shopping Cart":
			target.redeem_loyalty_points = 1
			target.loyalty_points = source.loyalty_points

		target.debit_to = get_party_account("Customer", source.customer, source.company)

	def update_item(source, target, source_parent):
		def get_billed_qty(so_item_name):
			table = frappe.qb.DocType("Sales Invoice Item")
			query = (
				frappe.qb.from_(table)
				.select(Sum(table.qty).as_("qty"))
				.where((table.docstatus == 1) & (table.so_detail == so_item_name))
			)
			return query.run(pluck="qty")[0] or 0

		if source_parent.has_unit_price_items:
			# 0 Amount rows (as seen in Unit Price Items) should be mapped as it is
			pending_amount = flt(source.amount) - flt(source.billed_amt)
			target.amount = pending_amount if flt(source.amount) else 0
		else:
			target.amount = flt(source.amount) - flt(source.billed_amt)

		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = (
			source.qty - get_billed_qty(source.name)
			if (source.qty and source.billed_amt)
			else (source.qty if is_unit_price_row(source) else source.qty - source.returned_qty)
		)

		if source_parent.project:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
		if target.item_code:
			item = get_item_defaults(target.item_code, source_parent.company)
			item_group = get_item_group_defaults(target.item_code, source_parent.company)
			cost_center = item.get("selling_cost_center") or item_group.get("selling_cost_center")

			if cost_center:
				target.cost_center = cost_center

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	def add_self_rm(doclist):
		parent = frappe.qb.DocType("Subcontracting Inward Order")
		child = frappe.qb.DocType("Subcontracting Inward Order Received Item")
		query = (
			frappe.qb.from_(parent)
			.join(child)
			.on(parent.name == child.parent)
			.select(
				child.required_qty,
				child.consumed_qty,
				child.billed_qty,
				child.rm_item_code,
				child.stock_uom,
				child.name,
			)
			.where(
				(parent.docstatus == 1)
				& (parent.sales_order == source_name)
				& (child.is_customer_provided_item == 0)
			)
		)
		result = query.run(as_dict=True)

		if result:
			idx = len(doclist.items) + 1
			for item in result:
				if (qty := max(item.required_qty, item.consumed_qty) - item.billed_qty) > 0:
					doclist.append(
						"items",
						{
							"item_code": item.rm_item_code,
							"qty": qty,
							"uom": item.stock_uom,
							"scio_detail": item.name,
						},
					)
					doclist.process_item_selection(idx)
					idx += 1
		doclist.has_subcontracted = 1

	doclist = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Sales Invoice",
				"field_map": {
					"party_account_currency": "party_account_currency",
				},
				"field_no_map": ["payment_terms_template"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Sales Order Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "so_detail",
					"parent": "sales_order",
				},
				"postprocess": update_item,
				"condition": lambda doc: (
					True
					if is_unit_price_row(doc)
					else (doc.qty and (doc.base_amount == 0 or abs(doc.billed_amt) < abs(doc.amount)))
				)
				and select_item(doc)
				and not args.get("skip_item_mapping"),
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"reset_value": True,
			},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
		},
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)

	if frappe.get_cached_value("Sales Order", source_name, "is_subcontracted"):
		add_self_rm(doclist)

	automatically_fetch_payment_terms = cint(
		frappe.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)
	if automatically_fetch_payment_terms:
		from erpnext.accounts.services.payment_schedule import PaymentScheduleService

		PaymentScheduleService(doclist).set_payment_schedule()

	return doclist


@frappe.whitelist()
def make_maintenance_schedule(source_name: str, target_doc: str | Document | None = None):
	maint_schedule = frappe.db.exists(
		"Maintenance Schedule Item", {"sales_order": source_name, "docstatus": 1}
	)

	if not maint_schedule:
		doclist = get_mapped_doc(
			"Sales Order",
			source_name,
			{
				"Sales Order": {"doctype": "Maintenance Schedule", "validation": {"docstatus": ["=", 1]}},
				"Sales Order Item": {
					"doctype": "Maintenance Schedule Item",
					"field_map": {"parent": "sales_order"},
				},
			},
			target_doc,
		)

		return doclist


@frappe.whitelist()
def make_maintenance_visit(source_name: str, target_doc: str | Document | None = None):
	MaintenanceVisit = frappe.qb.DocType("Maintenance Visit")
	MaintenanceVisitPurpose = frappe.qb.DocType("Maintenance Visit Purpose")

	query = (
		frappe.qb.from_(MaintenanceVisit)
		.join(MaintenanceVisitPurpose)
		.on(MaintenanceVisitPurpose.parent == MaintenanceVisit.name)
		.select(MaintenanceVisit.name)
		.where(MaintenanceVisitPurpose.prevdoc_docname == source_name)
		.where(MaintenanceVisit.docstatus == 1)
		.where(MaintenanceVisit.completion_status == "Fully Completed")
	)

	if not query.run():
		doclist = get_mapped_doc(
			"Sales Order",
			source_name,
			{
				"Sales Order": {"doctype": "Maintenance Visit", "validation": {"docstatus": ["=", 1]}},
				"Sales Order Item": {
					"doctype": "Maintenance Visit Purpose",
					"field_map": {"parent": "prevdoc_docname", "parenttype": "prevdoc_doctype"},
				},
			},
			target_doc,
		)

		return doclist


@frappe.whitelist()
def make_purchase_order(
	source_name: str, selected_items: str | list | None = None, target_doc: str | Document | None = None
):
	"""Creates Purchase Order for each Supplier. Returns a list of doc objects."""

	from erpnext.setup.utils import get_exchange_rate

	if not selected_items:
		return

	if isinstance(selected_items, str):
		selected_items = json.loads(selected_items)

	def set_missing_values(source, target):
		target.supplier = supplier
		company_currency = frappe.db.get_value(
			"Company", filters={"name": target.company}, fieldname=["default_currency"]
		)
		supplier_currency = frappe.db.get_value(
			"Supplier", filters={"name": supplier}, fieldname=["default_currency"]
		)

		target.currency = supplier_currency if supplier_currency else company_currency

		target.conversion_rate = get_exchange_rate(target.currency, company_currency, args="for_buying")

		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0
		target.inter_company_order_reference = ""
		target.shipping_rule = ""
		target.tc_name = ""
		target.terms = ""
		target.payment_schedule = []

		default_price_list = frappe.get_value("Supplier", supplier, "default_price_list")
		if default_price_list:
			target.buying_price_list = default_price_list

		default_payment_terms = frappe.get_value("Supplier", supplier, "payment_terms")
		if default_payment_terms:
			target.payment_terms_template = default_payment_terms

		if any(item.delivered_by_supplier for item in target.items):
			if source.shipping_address_name:
				target.shipping_address = source.shipping_address_name
				target.shipping_address_display = source.shipping_address
			else:
				target.shipping_address = source.customer_address
				target.shipping_address_display = source.address_display

			target.customer_contact_person = source.contact_person
			target.customer_contact_display = source.contact_display
			target.customer_contact_mobile = source.contact_mobile
			target.customer_contact_email = source.contact_email

		else:
			target.customer = ""
			target.customer_name = ""

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.schedule_date = source.delivery_date
		target.qty = flt(source.qty) - (flt(source.ordered_qty) / flt(source.conversion_factor))
		target.stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
		target.project = source_parent.project

	def update_item_for_packed_item(source, target, _):
		target.qty = flt(source.qty) - flt(source.ordered_qty)

	def filter_items(item, supplier):
		if (
			item.ordered_qty < item.stock_qty
			and not is_product_bundle(item.item_code)
			and items_to_map.get(item.item_code) == supplier
		):
			return True

		return False

	items_to_map = {
		item.get("item_code"): item.get("supplier") for item in selected_items if item.get("item_code")
	}
	item_codes = list(set(items_to_map.keys()))
	suppliers = list(set(items_to_map.values()))

	if not suppliers:
		suppliers = [None]

	purchase_orders = []
	for supplier in suppliers:
		doc = get_mapped_doc(
			"Sales Order",
			source_name,
			{
				"Sales Order": {
					"doctype": "Purchase Order",
					"field_no_map": [*CROSS_PARTY_FIELD_NO_MAP],
					"validation": {"docstatus": ["=", 1]},
				},
				"Sales Order Item": {
					"doctype": "Purchase Order Item",
					"field_map": [
						["name", "sales_order_item"],
						["parent", "sales_order"],
						["stock_uom", "stock_uom"],
						["uom", "uom"],
						["conversion_factor", "conversion_factor"],
						["delivery_date", "schedule_date"],
					],
					"field_no_map": [
						"rate",
						"price_list_rate",
						"item_tax_template",
						"discount_percentage",
						"discount_amount",
						"pricing_rules",
						"margin_type",
						"margin_rate_or_amount",
					],
					"postprocess": update_item,
					"condition": lambda doc, s=supplier: filter_items(doc, s),
				},
				"Packed Item": {
					"doctype": "Purchase Order Item",
					"field_map": [
						["name", "sales_order_packed_item"],
						["parent", "sales_order"],
						["uom", "uom"],
						["conversion_factor", "conversion_factor"],
						["product_bundle", "product_bundle"],
						["rate", "rate"],
					],
					"field_no_map": [
						"price_list_rate",
						"item_tax_template",
						"discount_percentage",
						"discount_amount",
						"supplier",
						"pricing_rules",
					],
					"postprocess": update_item_for_packed_item,
					"condition": lambda doc: doc.parent_item in item_codes
					and flt(doc.ordered_qty) < flt(doc.qty),
				},
			},
			target_doc,
			set_missing_values,
		)

		set_delivery_date(doc.items, source_name)
		if doc.supplier:
			doc.insert()
		purchase_orders.append(doc)

	return purchase_orders


def set_delivery_date(items: list, sales_order: str) -> None:
	# `product_bundle` now holds the Product Bundle *version*, so match the Purchase
	# Order rows to their originating Sales Order rows by that version.
	delivery_dates = frappe.get_all(
		"Sales Order Item", filters={"parent": sales_order}, fields=["delivery_date", "product_bundle"]
	)

	delivery_by_bundle = frappe._dict()
	for date in delivery_dates:
		if date.product_bundle:
			delivery_by_bundle[date.product_bundle] = date.delivery_date

	for item in items:
		if item.product_bundle:
			item.schedule_date = delivery_by_bundle.get(item.product_bundle)


@frappe.whitelist()
def make_work_orders(items: str, sales_order: str, company: str, project: str | None = None):
	"""Make Work Orders against the given Sales Order for the given `items`"""
	items = json.loads(items).get("items")
	out = []

	for i in items:
		if not i.get("bom"):
			frappe.throw(_("Please select BOM against item {0}").format(i.get("item_code")))
		if not i.get("pending_qty"):
			frappe.throw(_("Please select Qty against item {0}").format(i.get("item_code")))

		work_order = frappe.get_doc(
			doctype="Work Order",
			production_item=i["item_code"],
			bom_no=i.get("bom"),
			qty=i["pending_qty"],
			company=company,
			sales_order=sales_order,
			sales_order_item=i["sales_order_item"],
			project=project,
			fg_warehouse=i["warehouse"],
			description=i["description"],
		).insert()
		work_order.set_work_order_operations()
		work_order.flags.ignore_mandatory = True
		work_order.save()
		out.append(work_order)

	return [p.name for p in out]


@frappe.whitelist()
def make_production_plan(source_name: str, target_doc: str | Document | None = None):
	sales_order = frappe.get_doc("Sales Order", source_name)

	production_plan = frappe.new_doc(
		"Production Plan",
		company=sales_order.company,
		get_items_from="Sales Order",
		posting_date=nowdate(),
	)

	open_so = [data.name for data in get_sales_orders(production_plan)]
	if sales_order.name not in open_so:
		frappe.throw(_("Sales Order {0} is not available for production").format(sales_order.name))

	production_plan.append(
		"sales_orders",
		{
			"sales_order": sales_order.name,
			"sales_order_date": sales_order.transaction_date,
			"customer": sales_order.customer,
			"grand_total": sales_order.base_grand_total,
		},
	)
	production_plan.get_items()
	if not production_plan.get("po_items"):
		frappe.throw(_("Sales Order {0} is not available for production").format(sales_order.name))

	return production_plan


@frappe.whitelist()
def make_raw_material_request(
	items: str | frappe._dict, company: str, sales_order: str, project: str | None = None
):
	if not frappe.has_permission("Sales Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(items, str):
		items = frappe._dict(json.loads(items))

	for item in items.get("items"):
		item["include_exploded_items"] = items.get("include_exploded_items")
		item["ignore_existing_ordered_qty"] = items.get("ignore_existing_ordered_qty")
		item["include_raw_materials_from_sales_order"] = items.get("include_raw_materials_from_sales_order")

	items.update({"company": company, "sales_order": sales_order})

	item_wh = {}
	for item in items.get("items"):
		if item.get("warehouse"):
			item_wh[item.get("item_code")] = item.get("warehouse")

	raw_materials = get_items_for_material_requests(items)
	if not raw_materials:
		frappe.msgprint(_("Material Request not created, as quantity for Raw Materials already available."))
		return

	material_request = frappe.new_doc("Material Request")
	material_request.update(
		dict(
			doctype="Material Request",
			transaction_date=nowdate(),
			company=company,
			material_request_type="Purchase",
		)
	)
	for item in raw_materials:
		item_doc = frappe.get_cached_doc("Item", item.get("item_code"))

		schedule_date = add_days(nowdate(), cint(item_doc.lead_time_days))
		row = material_request.append(
			"items",
			{
				"item_code": item.get("item_code"),
				"qty": item.get("quantity"),
				"schedule_date": schedule_date,
				"warehouse": item_wh.get(item.get("main_bom_item")) or item.get("warehouse"),
				"sales_order": sales_order,
				"project": project,
			},
		)

		if not (strip_html(item.get("description")) and strip_html(item_doc.description)):
			row.description = item_doc.item_name or item.get("item_code")

	material_request.insert()
	material_request.flags.ignore_permissions = 1
	material_request.run_method("set_missing_values")
	material_request.submit()
	return material_request


@frappe.whitelist()
def make_inter_company_purchase_order(source_name: str, target_doc: str | Document | None = None):
	from erpnext.accounts.doctype.sales_invoice.mapper import make_inter_company_transaction

	return make_inter_company_transaction("Sales Order", source_name, target_doc)


@frappe.whitelist()
def create_pick_list(source_name: str, target_doc: str | Document | None = None):
	def validate_sales_order():
		so = frappe.get_doc("Sales Order", source_name)
		for item in so.items:
			if item.stock_reserved_qty > 0:
				frappe.throw(
					_(
						"Cannot create a pick list for Sales Order {0} because it has reserved stock. Please unreserve the stock in order to create a pick list."
					).format(frappe.bold(source_name))
				)

	def update_item_quantity(source, target, source_parent) -> None:
		picked_qty = flt(source.picked_qty) / (flt(source.conversion_factor) or 1)
		qty_to_be_picked = flt(source.qty) - max(picked_qty, flt(source.delivered_qty))

		target.qty = qty_to_be_picked
		target.stock_qty = qty_to_be_picked * flt(source.conversion_factor)

		# update available qty
		bin_details = get_bin_details(source.item_code, source.warehouse, source_parent.company)
		target.actual_qty = bin_details.get("actual_qty")
		target.company_total_stock = bin_details.get("company_total_stock")

	def update_packed_item_qty(source, target, source_parent) -> None:
		qty = flt(source.qty)
		for item in source_parent.items:
			if source.parent_detail_docname == item.name:
				picked_qty = flt(item.picked_qty) / (flt(item.conversion_factor) or 1)
				pending_percent = (item.qty - max(picked_qty, item.delivered_qty)) / item.qty
				target.qty = target.stock_qty = qty * pending_percent
				return

	def should_pick_order_item(item) -> bool:
		return (
			abs(item.delivered_qty) < abs(item.qty)
			and item.delivered_by_supplier != 1
			and not is_product_bundle(item.item_code)
		)

	# Don't allow a Pick List to be created against a Sales Order that has reserved stock.
	validate_sales_order()

	doc = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Pick List",
				"field_map": {"set_warehouse": "parent_warehouse"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Sales Order Item": {
				"doctype": "Pick List Item",
				"field_map": {"parent": "sales_order", "name": "sales_order_item"},
				"postprocess": update_item_quantity,
				"condition": should_pick_order_item,
			},
			"Packed Item": {
				"doctype": "Pick List Item",
				"field_map": {
					"parent": "sales_order",
					"parent_detail_docname": "sales_order_item",
					"name": "product_bundle_item",
				},
				"field_no_map": ["picked_qty"],
				"postprocess": update_packed_item_qty,
			},
		},
		target_doc,
	)

	doc.purpose = "Delivery"

	doc.set_item_locations()

	return doc


@frappe.whitelist()
def make_subcontracting_inward_order(source_name: str, target_doc: str | Document | None = None):
	if not is_so_fully_subcontracted(source_name):
		return get_mapped_subcontracting_inward_order(source_name, target_doc)
	else:
		frappe.throw(_("This Sales Order has been fully subcontracted."))


def is_so_fully_subcontracted(so_name: str) -> bool:
	table = frappe.qb.DocType("Sales Order Item")
	query = (
		frappe.qb.from_(table)
		.select(table.name)
		.where((table.parent == so_name) & (table.qty != table.subcontracted_qty))
	)
	return not query.run(as_dict=True)


def get_mapped_subcontracting_inward_order(
	source_name: str, target_doc: str | Document | None = None
) -> Document:
	def post_process(source_doc, target_doc):
		if (
			frappe.db.count(
				"Warehouse", {"customer": source_doc.customer, "disabled": 0, "is_rejected_warehouse": 0}
			)
			== 1
		):
			target_doc.customer_warehouse = frappe.get_cached_value(
				"Warehouse",
				{"customer": source_doc.customer, "disabled": 0, "is_rejected_warehouse": 0},
				"name",
			)
		target_doc.populate_items_table()

	if target_doc and isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
		for key in ["service_items", "items", "received_items"]:
			if key in target_doc:
				del target_doc[key]
		target_doc = json.dumps(target_doc)

	target_doc = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Subcontracting Inward Order",
				"field_map": {},
				"field_no_map": ["total_qty", "total", "net_total"],
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Sales Order Item": {
				"doctype": "Subcontracting Inward Order Service Item",
				"field_map": {
					"name": "sales_order_item",
				},
				"field_no_map": ["qty", "fg_item_qty", "amount"],
				"condition": lambda item: item.qty != item.subcontracted_qty,
			},
		},
		target_doc,
		post_process,
	)

	return target_doc
