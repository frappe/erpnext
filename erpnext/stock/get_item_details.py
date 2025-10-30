# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
import typing
from functools import WRAPPER_ASSIGNMENTS, wraps

import frappe
from frappe import _, throw
from frappe.model import child_table_fields, default_fields
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.model.utils import get_fetch_values
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import add_days, add_months, cint, cstr, flt, getdate, parse_json

import erpnext
from erpnext import get_company_currency
from erpnext.accounts.doctype.pricing_rule.pricing_rule import (
	get_pricing_rule_for_item,
	set_transaction_type,
)
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.item.item import get_item_defaults, get_uom_conv_factor
from erpnext.stock.doctype.item_manufacturer.item_manufacturer import get_item_manufacturer_part_no
from erpnext.stock.doctype.price_list.price_list import get_price_list_details

ItemDetails = frappe._dict
ItemDetailsCtx = frappe._dict
ItemPriceCtx = frappe._dict

sales_doctypes = ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "POS Invoice"]
purchase_doctypes = [
	"Material Request",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
]


def _preprocess_ctx(ctx):
	if not ctx.price_list:
		ctx.price_list = ctx.selling_price_list or ctx.buying_price_list

	if not ctx.item_code and ctx.barcode:
		ctx.item_code = get_item_code(barcode=ctx.barcode)
	elif not ctx.item_code and ctx.serial_no:
		ctx.item_code = get_item_code(serial_no=ctx.serial_no)

	set_transaction_type(ctx)


@frappe.whitelist()
@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_item_details(
	ctx: ItemDetailsCtx, doc=None, for_validate=False, overwrite_warehouse=True
) -> ItemDetails:
	"""
	ctx = {
	        "item_code": "",
	        "warehouse": None,
	        "customer": "",
	        "conversion_rate": 1.0,
	        "selling_price_list": None,
	        "price_list_currency": None,
	        "plc_conversion_rate": 1.0,
	        "doctype": "",
	        "name": "",
	        "supplier": None,
	        "transaction_date": None,
	        "conversion_rate": 1.0,
	        "buying_price_list": None,
	        "is_subcontracted": 0/1,
	        "ignore_pricing_rule": 0/1
	        "project": ""
	        "set_warehouse": ""
	}
	"""
	_preprocess_ctx(ctx)
	for_validate = parse_json(for_validate)
	overwrite_warehouse = parse_json(overwrite_warehouse)
	item = frappe.get_cached_doc("Item", ctx.item_code)
	validate_item_details(ctx, item)

	if isinstance(doc, str):
		doc = json.loads(doc)

	if doc:
		ctx.transaction_date = doc.get("transaction_date") or doc.get("posting_date")

		if doc.get("doctype") == "Purchase Invoice":
			ctx.bill_date = doc.get("bill_date")

	out: ItemDetails = get_basic_details(ctx, item, overwrite_warehouse)

	get_item_tax_template(ctx, item, out)
	out.item_tax_rate = get_item_tax_map(
		doc=doc or ctx,
		tax_template=out.item_tax_template or ctx.item_tax_template,
		as_json=True,
	)

	get_party_item_code(ctx, item, out)

	if ctx.doctype in ["Sales Order", "Quotation"]:
		set_valuation_rate(out, ctx)

	update_party_blanket_order(ctx, out)

	# Never try to find a customer price if customer is set in these Doctype
	current_customer = ctx.customer
	if ctx.doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
		ctx.customer = None

	out.update(get_price_list_rate(ctx, item))

	if (
		not out.price_list_rate
		and ctx.transaction_type == "selling"
		and frappe.get_single_value("Selling Settings", "fallback_to_default_price_list")
	):
		fallback_args = ctx.copy()
		fallback_args.price_list = frappe.get_single_value("Selling Settings", "selling_price_list")
		out.update(get_price_list_rate(fallback_args, item))

	ctx.customer = current_customer

	if ctx.customer and cint(ctx.is_pos):
		out.update(get_pos_profile_item_details_(ctx, ctx.company, update_data=True))

	if item.is_stock_item:
		update_bin_details(ctx, out, doc)

	# update ctx with out, if key or value not exists
	for key, value in out.items():
		if ctx.get(key) is None:
			ctx[key] = value

	data = get_pricing_rule_for_item(ctx, doc=doc, for_validate=for_validate)

	out.update(data)

	if (
		frappe.get_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward")
		and not ctx.get("serial_and_batch_bundle")
		and (ctx.get("use_serial_batch_fields") or ctx.get("doctype") == "POS Invoice")
	):
		update_stock(ctx, out, doc)

	if ctx.transaction_date and item.lead_time_days:
		out.schedule_date = out.lead_time_date = add_days(ctx.transaction_date, item.lead_time_days)

	if ctx.is_subcontracted:
		out.bom = ctx.bom or get_default_bom(ctx.item_code)

	get_gross_profit(out)
	if ctx.doctype == "Material Request":
		out.rate = ctx.rate or out.price_list_rate
		out.amount = flt(ctx.qty) * flt(out.rate)

	out = remove_standard_fields(out)
	return out


def remove_standard_fields(out: ItemDetails):
	for key in child_table_fields + default_fields:
		out.pop(key, None)
	return out


def set_valuation_rate(out: ItemDetails | dict, ctx: ItemDetailsCtx):
	if frappe.db.exists("Product Bundle", {"name": ctx.item_code, "disabled": 0}, cache=True):
		valuation_rate = 0.0
		bundled_items = frappe.get_doc("Product Bundle", ctx.item_code)

		for bundle_item in bundled_items.items:
			valuation_rate += flt(
				get_valuation_rate(bundle_item.item_code, ctx.company, out.get("warehouse")).get(
					"valuation_rate"
				)
				* bundle_item.qty
			)

		out.update({"valuation_rate": valuation_rate})

	else:
		out.update(get_valuation_rate(ctx.item_code, ctx.company, out.get("warehouse")))


def update_stock(ctx, out, doc=None):
	from erpnext.stock.doctype.batch.batch import get_available_batches
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos_for_outward

	if (
		(
			ctx.get("doctype") in ["Delivery Note", "POS Invoice"]
			or (ctx.get("doctype") == "Sales Invoice" and ctx.get("update_stock"))
		)
		and out.warehouse
		and out.stock_qty > 0
	):
		if doc and isinstance(doc, dict):
			doc = frappe._dict(doc)

		kwargs = frappe._dict(
			{
				"item_code": ctx.item_code,
				"warehouse": ctx.warehouse,
				"based_on": frappe.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
				"sabb_voucher_no": doc.get("name") if doc else None,
				"sabb_voucher_detail_no": ctx.child_docname,
				"sabb_voucher_type": ctx.doctype,
				"pick_reserved_items": True,
			}
		)

		if ctx.get("doctype") == "Delivery Note":
			kwargs["against_sales_order"] = ctx.get("against_sales_order")

		if ctx.get("ignore_serial_nos"):
			kwargs["ignore_serial_nos"] = ctx.get("ignore_serial_nos")

		qty = out.stock_qty
		batches = []
		if out.has_batch_no and not ctx.get("batch_no"):
			batches = get_available_batches(kwargs)
			if doc:
				filter_batches(batches, doc)

			for batch_no, batch_qty in batches.items():
				rate = get_batch_based_item_price(
					{"price_list": doc.get("selling_price_list"), "uom": out.uom, "batch_no": batch_no},
					out.item_code,
				)
				if batch_qty >= qty:
					out.update({"batch_no": batch_no, "actual_batch_qty": qty})
					if rate:
						out.update({"rate": rate, "price_list_rate": rate})
					break
				else:
					qty -= batch_qty

				out.update({"batch_no": batch_no, "actual_batch_qty": batch_qty})
				if rate:
					out.update({"rate": rate, "price_list_rate": rate})

		if out.has_serial_no and out.has_batch_no and has_incorrect_serial_nos(ctx, out):
			kwargs["batches"] = [ctx.get("batch_no")] if ctx.get("batch_no") else [out.get("batch_no")]
			serial_nos = get_serial_nos_for_outward(kwargs)
			serial_nos = get_filtered_serial_nos(serial_nos, doc)

			out["serial_no"] = "\n".join(serial_nos[: cint(out.stock_qty)])

		elif out.has_serial_no and not ctx.get("serial_no"):
			serial_nos = get_serial_nos_for_outward(kwargs)
			serial_nos = get_filtered_serial_nos(serial_nos, doc)

			out["serial_no"] = "\n".join(serial_nos[: cint(out.stock_qty)])


def has_incorrect_serial_nos(ctx, out):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	if not ctx.get("serial_no"):
		return True

	serial_nos = get_serial_nos(ctx.get("serial_no"))
	if len(serial_nos) != out.get("stock_qty"):
		return True

	return False


def filter_batches(batches, doc):
	for row in doc.get("items"):
		if row.get("batch_no") in batches:
			batches[row.get("batch_no")] -= row.get("qty")
			if batches[row.get("batch_no")] <= 0:
				del batches[row.get("batch_no")]


def get_filtered_serial_nos(serial_nos, doc, table=None):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	if not table:
		table = "items"

	for row in doc.get(table):
		if row.get("serial_no"):
			for serial_no in get_serial_nos(row.get("serial_no")):
				if serial_no in serial_nos:
					serial_nos.remove(serial_no)

	return serial_nos


def update_bin_details(ctx: ItemDetailsCtx, out: ItemDetails, doc):
	if ctx.doctype == "Material Request" and ctx.material_request_type == "Material Transfer":
		out.update(get_bin_details(ctx.item_code, ctx.from_warehouse))

	elif out.get("warehouse"):
		company = ctx.company if (doc and doc.get("doctype") == "Purchase Order") else None

		# calculate company_total_stock only for po
		bin_details = get_bin_details(ctx.item_code, out.warehouse, company, include_child_warehouses=True)

		out.update(bin_details)


def get_item_code(barcode=None, serial_no=None):
	if barcode:
		item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, fieldname=["parent"])
		if not item_code:
			frappe.throw(_("No Item with Barcode {0}").format(barcode))
	elif serial_no:
		item_code = frappe.db.get_value("Serial No", serial_no, "item_code")
		if not item_code:
			frappe.throw(_("No Item with Serial No {0}").format(serial_no))

	return item_code


def validate_item_details(ctx: ItemDetailsCtx, item):
	if not ctx.company:
		throw(_("Please specify Company"))

	from erpnext.stock.doctype.item.item import validate_end_of_life

	validate_end_of_life(item.name, item.end_of_life, item.disabled)

	if cint(item.has_variants):
		msg = f"Item {item.name} is a template, please select one of its variants"

		throw(_(msg), title=_("Template Item Selected"))

	elif ctx.doctype != "Material Request":
		if ctx.is_subcontracted:
			if ctx.is_old_subcontracting_flow:
				if item.is_sub_contracted_item != 1:
					throw(_("Item {0} must be a Sub-contracted Item").format(item.name))
			else:
				if item.is_stock_item:
					throw(_("Item {0} must be a Non-Stock Item").format(item.name))


def get_basic_details(ctx: ItemDetailsCtx, item, overwrite_warehouse=True) -> ItemDetails:
	"""
	:param ctx: {
	                "item_code": "",
	                "warehouse": None,
	                "customer": "",
	                "conversion_rate": 1.0,
	                "selling_price_list": None,
	                "price_list_currency": None,
	                "price_list_uom_dependant": None,
	                "plc_conversion_rate": 1.0,
	                "doctype": "",
	                "name": "",
	                "supplier": None,
	                "transaction_date": None,
	                "conversion_rate": 1.0,
	                "buying_price_list": None,
	                "is_subcontracted": 0/1,
	                "ignore_pricing_rule": 0/1
	                "project": "",
	                barcode: "",
	                serial_no: "",
	                currency: "",
	                update_stock: "",
	                price_list: "",
	                company: "",
	                order_type: "",
	                is_pos: "",
	                project: "",
	                qty: "",
	                stock_qty: "",
	                conversion_factor: "",
	                against_blanket_order: 0/1
	        }
	:param item: `item_code` of Item object
	:return: frappe._dict
	"""

	if not item:
		item = frappe.get_cached_doc("Item", ctx.item_code)

	if item.variant_of and not item.taxes and frappe.db.exists("Item Tax", {"parent": item.variant_of}):
		item.update_template_tables()

	item_defaults = get_item_defaults(item.name, ctx.company)
	item_group_defaults = get_item_group_defaults(item.name, ctx.company)
	brand_defaults = get_brand_defaults(item.name, ctx.company)

	defaults = frappe._dict(
		{
			"item_defaults": item_defaults,
			"item_group_defaults": item_group_defaults,
			"brand_defaults": brand_defaults,
		}
	)

	warehouse = get_item_warehouse_(ctx, item, overwrite_warehouse, defaults)

	if ctx.doctype == "Material Request" and not ctx.material_request_type:
		ctx["material_request_type"] = frappe.db.get_value(
			"Material Request", ctx.name, "material_request_type", cache=True
		)

	expense_account = None

	if item.is_fixed_asset:
		from erpnext.assets.doctype.asset.asset import get_asset_account, is_cwip_accounting_enabled

		if is_cwip_accounting_enabled(item.asset_category):
			expense_account = get_asset_account(
				"capital_work_in_progress_account",
				asset_category=item.asset_category,
				company=ctx.company,
			)
		elif ctx.doctype in (
			"Purchase Invoice",
			"Purchase Receipt",
			"Purchase Order",
			"Material Request",
		):
			from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account

			expense_account = get_asset_category_account(
				fieldname="fixed_asset_account", item=ctx.item_code, company=ctx.company
			)

	# Set the UOM to the Default Sales UOM or Default Purchase UOM if configured in the Item Master
	if not ctx.uom:
		if ctx.doctype in sales_doctypes:
			ctx.uom = item.sales_uom if item.sales_uom else item.stock_uom
		elif (ctx.doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]) or (
			ctx.doctype == "Material Request" and ctx.material_request_type == "Purchase"
		):
			ctx.uom = item.purchase_uom if item.purchase_uom else item.stock_uom
		else:
			ctx.uom = item.stock_uom

	# Set stock UOM in ctx, so that it can be used while fetching item price
	ctx.stock_uom = item.stock_uom

	if ctx.batch_no and item.name != frappe.get_cached_value("Batch", ctx.batch_no, "item"):
		ctx.batch_no = ""

	out = ItemDetails(
		{
			"item_code": item.name,
			"item_name": item.item_name,
			"description": cstr(item.description).strip(),
			"image": cstr(item.image).strip(),
			"warehouse": warehouse,
			"income_account": get_default_income_account(
				ctx, item_defaults, item_group_defaults, brand_defaults
			),
			"expense_account": expense_account
			or get_default_expense_account(ctx, item_defaults, item_group_defaults, brand_defaults),
			"discount_account": get_default_discount_account(
				ctx, item_defaults, item_group_defaults, brand_defaults
			),
			"provisional_expense_account": get_provisional_account(
				ctx, item_defaults, item_group_defaults, brand_defaults
			),
			"cost_center": get_default_cost_center(ctx, item_defaults, item_group_defaults, brand_defaults),
			"has_serial_no": item.has_serial_no,
			"has_batch_no": item.has_batch_no,
			"batch_no": ctx.batch_no,
			"uom": ctx.uom,
			"stock_uom": item.stock_uom,
			"min_order_qty": flt(item.min_order_qty) if ctx.doctype == "Material Request" else "",
			"qty": flt(ctx.qty) or 1.0,
			"stock_qty": flt(ctx.qty) or 1.0,
			"price_list_rate": 0.0,
			"base_price_list_rate": 0.0,
			"rate": 0.0,
			"base_rate": 0.0,
			"amount": 0.0,
			"base_amount": 0.0,
			"net_rate": 0.0,
			"net_amount": 0.0,
			"discount_percentage": 0.0,
			"discount_amount": flt(ctx.discount_amount) or 0.0,
			"update_stock": ctx.update_stock if ctx.doctype in ["Sales Invoice", "Purchase Invoice"] else 0,
			"delivered_by_supplier": item.delivered_by_supplier
			if ctx.doctype in ["Sales Order", "Sales Invoice"]
			else 0,
			"is_fixed_asset": item.is_fixed_asset,
			"last_purchase_rate": item.last_purchase_rate if ctx.doctype in ["Purchase Order"] else 0,
			"transaction_date": ctx.transaction_date,
			"against_blanket_order": ctx.against_blanket_order,
			"bom_no": item.get("default_bom"),
			"weight_per_unit": ctx.weight_per_unit or item.get("weight_per_unit"),
			"weight_uom": ctx.weight_uom or item.get("weight_uom"),
			"grant_commission": item.get("grant_commission"),
		}
	)

	if not item.is_stock_item and not out.expense_account:
		out.expense_account = frappe.get_cached_value("Company", ctx.company, "service_expense_account")

	default_supplier = get_default_supplier(ctx, item_defaults, item_group_defaults, brand_defaults)
	if default_supplier:
		out.supplier = default_supplier

	if item.get("enable_deferred_revenue") or item.get("enable_deferred_expense"):
		out.update(calculate_service_end_date(ctx, item))

	# calculate conversion factor
	if item.stock_uom == ctx.uom:
		out.conversion_factor = 1.0
	else:
		out.conversion_factor = ctx.conversion_factor or get_conversion_factor(item.name, ctx.uom).get(
			"conversion_factor"
		)

	ctx.conversion_factor = out.conversion_factor
	out.stock_qty = out.qty * out.conversion_factor
	ctx.stock_qty = out.stock_qty

	# calculate last purchase rate
	if ctx.doctype in purchase_doctypes and not frappe.db.get_single_value(
		"Buying Settings", "disable_last_purchase_rate"
	):
		from erpnext.buying.doctype.purchase_order.purchase_order import item_last_purchase_rate

		out.last_purchase_rate = item_last_purchase_rate(
			ctx.name, ctx.conversion_rate, item.name, out.conversion_factor
		)

	# if default specified in item is for another company, fetch from company
	for d in [
		["Account", "income_account", "default_income_account"],
		["Account", "expense_account", "default_expense_account"],
		["Cost Center", "cost_center", "cost_center"],
		["Warehouse", "warehouse", ""],
	]:
		if not out[d[1]]:
			out[d[1]] = frappe.get_cached_value("Company", ctx.company, d[2]) if d[2] else None

	for fieldname in ("item_name", "item_group", "brand", "stock_uom"):
		out[fieldname] = item.get(fieldname)

	if ctx.manufacturer:
		part_no = get_item_manufacturer_part_no(ctx.item_code, ctx.manufacturer)
		if part_no:
			out.manufacturer_part_no = part_no
		else:
			out.manufacturer_part_no = None
			out.manufacturer = None
	else:
		data = frappe.get_cached_value(
			"Item", item.name, ["default_item_manufacturer", "default_manufacturer_part_no"], as_dict=True
		)

		if data:
			out.update(
				{
					"manufacturer": data.default_item_manufacturer,
					"manufacturer_part_no": data.default_manufacturer_part_no,
				}
			)

	child_doctype = ctx.doctype + " Item"
	meta = frappe.get_meta(child_doctype)
	if meta.get_field("barcode"):
		update_barcode_value(out)

	if out.weight_per_unit:
		out.total_weight = out.weight_per_unit * out.stock_qty

	return out


from erpnext.deprecation_dumpster import get_item_warehouse


@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_item_warehouse_(ctx: ItemDetailsCtx, item, overwrite_warehouse, defaults=None):
	if not defaults:
		defaults = frappe._dict(
			{
				"item_defaults": get_item_defaults(item.name, ctx.company),
				"item_group_defaults": get_item_group_defaults(item.name, ctx.company),
				"brand_defaults": get_brand_defaults(item.name, ctx.company),
			}
		)

	if overwrite_warehouse or not ctx.warehouse:
		warehouse = (
			ctx.set_warehouse
			or defaults.item_defaults.get("default_warehouse")
			or defaults.item_group_defaults.get("default_warehouse")
			or defaults.brand_defaults.get("default_warehouse")
			or ctx.warehouse
		)

	else:
		warehouse = ctx.warehouse

	if not warehouse:
		default_warehouse = frappe.get_single_value("Stock Settings", "default_warehouse")
		if (
			default_warehouse
			and frappe.get_cached_value("Warehouse", default_warehouse, "company") == ctx.company
		):
			return default_warehouse

	return warehouse


def update_barcode_value(out):
	barcode_data = get_barcode_data([out])

	# If item has one barcode then update the value of the barcode field
	if barcode_data and len(barcode_data.get(out.item_code)) == 1:
		out["barcode"] = barcode_data.get(out.item_code)[0]


def get_barcode_data(items_list=None, item_code=None):
	# get item-wise batch no data
	# example: {'LED-GRE': [Batch001, Batch002]}
	# where LED-GRE is item code, SN0001 is serial no and Pune is warehouse

	itemwise_barcode = {}
	if not items_list and item_code:
		_dict_item_code = frappe._dict(
			{
				"item_code": item_code,
			}
		)

		items_list = [frappe._dict(_dict_item_code)]

	for item in items_list:
		barcodes = frappe.db.get_all("Item Barcode", filters={"parent": item.item_code}, fields="barcode")

		for barcode in barcodes:
			if item.item_code not in itemwise_barcode:
				itemwise_barcode.setdefault(item.item_code, [])
			itemwise_barcode[item.item_code].append(barcode.get("barcode"))

	return itemwise_barcode


@frappe.whitelist()
def get_item_tax_info(doc, tax_category, item_codes, item_rates=None, item_tax_templates=None):
	out = {}

	if item_tax_templates is None:
		item_tax_templates = {}

	if item_rates is None:
		item_rates = {}

	doc = parse_json(doc)
	item_codes = parse_json(item_codes)
	item_rates = parse_json(item_rates)
	item_tax_templates = parse_json(item_tax_templates)

	for item_code in item_codes:
		if not item_code or item_code[1] in out or not item_tax_templates.get(item_code[1]):
			continue

		out[item_code[1]] = ItemDetails()
		item = frappe.get_cached_doc("Item", item_code[0])
		ctx: ItemDetailsCtx = {
			"company": doc.company,
			"tax_category": tax_category,
			"base_net_rate": item_rates.get(item_code[1]),
		}

		if item_tax_templates:
			ctx.update({"item_tax_template": item_tax_templates.get(item_code[1])})

		get_item_tax_template(ctx, item, out[item_code[1]])
		out[item_code[1]]["item_tax_rate"] = get_item_tax_map(
			doc=doc,
			tax_template=out[item_code[1]].get("item_tax_template"),
			as_json=True,
		)

	return out


@frappe.whitelist()
@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_item_tax_template(ctx: ItemDetailsCtx, item=None, out: ItemDetails | None = None):
	"""
	Determines item_tax template from item or parent item groups.

	Accesses:
	        ctx = {
	        "child_doctype": str
	        }
	Passes:
	        ctx = {
	                "company": str
	                "bill_date": str
	                "transaction_date": str
	        "tax_category": None
	        "item_tax_template": None
	        "base_net_rate": float
	        }
	"""
	if not item:
		if not ctx.get("item_code"):
			frappe.throw(_("Item/Item Code required to get Item Tax Template."))
		else:
			item = frappe.get_cached_doc("Item", ctx.item_code)

	item_tax_template = None
	if item.taxes:
		item_tax_template = _get_item_tax_template(ctx, item.taxes, out)

	if not item_tax_template:
		item_group = item.item_group
		while item_group and not item_tax_template:
			item_group_doc = frappe.get_cached_doc("Item Group", item_group)
			item_tax_template = _get_item_tax_template(ctx, item_group_doc.taxes, out)
			item_group = item_group_doc.parent_item_group

	if out and ctx.get("child_doctype") and item_tax_template:
		out.update(get_fetch_values(ctx.get("child_doctype"), "item_tax_template", item_tax_template))

	return item_tax_template


@erpnext.normalize_ctx_input(ItemDetailsCtx)
def _get_item_tax_template(
	ctx: ItemDetailsCtx, taxes, out: ItemDetails | None = None, for_validate=False
) -> None | str | list[str]:
	"""
	Accesses:
	        ctx = {
	                "company": str
	                "bill_date": str
	                "transaction_date": str
	        "tax_category": None
	        "item_tax_template": None
	        }
	Passes:
	        ctx = {
	        "base_net_rate": float
	        }
	"""
	if out is None:
		out = ItemDetails()
	taxes_with_validity = []
	taxes_with_no_validity = []

	for tax in taxes:
		disabled, tax_company = frappe.get_cached_value(
			"Item Tax Template", tax.item_tax_template, ["disabled", "company"]
		)
		if not disabled and tax_company == ctx["company"]:
			if tax.valid_from or tax.maximum_net_rate:
				# In purchase Invoice first preference will be given to supplier invoice date
				# if supplier date is not present then posting date
				validation_date = (
					ctx.get("bill_date") or ctx.get("posting_date") or ctx.get("transaction_date")
				)

				if getdate(tax.valid_from) <= getdate(validation_date) and is_within_valid_range(ctx, tax):
					taxes_with_validity.append(tax)
			else:
				taxes_with_no_validity.append(tax)

	if taxes_with_validity:
		taxes = sorted(taxes_with_validity, key=lambda i: i.valid_from or tax.maximum_net_rate, reverse=True)
	else:
		taxes = taxes_with_no_validity

	if for_validate:
		return [
			tax.item_tax_template
			for tax in taxes
			if (
				cstr(tax.tax_category) == cstr(ctx.get("tax_category"))
				and (tax.item_tax_template not in taxes)
			)
		]

	# all templates have validity and no template is valid
	if not taxes_with_validity and (not taxes_with_no_validity):
		return None

	# do not change if already a valid template
	if ctx.get("item_tax_template") in {t.item_tax_template for t in taxes}:
		out.item_tax_template = ctx.get("item_tax_template")
		return ctx.get("item_tax_template")

	for tax in taxes:
		if cstr(tax.tax_category) == cstr(ctx.get("tax_category")):
			out.item_tax_template = tax.item_tax_template
			return tax.item_tax_template
	return None


@erpnext.normalize_ctx_input(ItemDetailsCtx)
def is_within_valid_range(ctx: ItemDetailsCtx, tax) -> bool:
	"""
	Accesses:
	        ctx = {
	        "base_net_rate": float
	        }
	"""

	if not flt(tax.maximum_net_rate):
		# No range specified, just ignore
		return True
	elif flt(tax.minimum_net_rate) <= flt(ctx.get("base_net_rate")) <= flt(tax.maximum_net_rate):
		return True

	return False


@frappe.whitelist()
def get_item_tax_map(*, doc: str | dict | Document, tax_template: str | None = None, as_json=True):
	doc = parse_json(doc)
	item_tax_map = {}
	for t in (t for t in (doc.get("taxes") or []) if not t.get("set_by_item_tax_template")):
		item_tax_map[t.get("account_head")] = t.get("rate")

	if tax_template:
		template = frappe.get_cached_doc("Item Tax Template", tax_template)
		for d in template.taxes:
			if frappe.get_cached_value("Account", d.tax_type, "company") == doc.get("company"):
				item_tax_map[d.tax_type] = d.tax_rate

	return json.dumps(item_tax_map) if as_json else item_tax_map


@frappe.whitelist()
@erpnext.normalize_ctx_input(ItemDetailsCtx)
def calculate_service_end_date(ctx: ItemDetailsCtx, item=None):
	_preprocess_ctx(ctx)
	if not item:
		item = frappe.get_cached_doc("Item", ctx.item_code)

	doctype = ctx.parenttype or ctx.doctype
	if doctype == "Sales Invoice":
		enable_deferred = "enable_deferred_revenue"
		no_of_months = "no_of_months"
		account = "deferred_revenue_account"
	else:
		enable_deferred = "enable_deferred_expense"
		no_of_months = "no_of_months_exp"
		account = "deferred_expense_account"

	service_start_date = ctx.service_start_date if ctx.service_start_date else ctx.transaction_date
	service_end_date = add_months(service_start_date, item.get(no_of_months))
	deferred_detail = {"service_start_date": service_start_date, "service_end_date": service_end_date}
	deferred_detail[enable_deferred] = item.get(enable_deferred)
	deferred_detail[account] = get_default_deferred_account(ctx, item, fieldname=account)

	return deferred_detail


def get_default_income_account(ctx: ItemDetailsCtx, item, item_group, brand):
	return (
		item.get("income_account")
		or item_group.get("income_account")
		or brand.get("income_account")
		or ctx.income_account
	)


def get_default_inventory_account(ctx: ItemDetailsCtx, item, item_group, brand):
	if not frappe.get_cached_value("Company", ctx.company, "enable_item_wise_inventory_account"):
		return None

	return (
		ctx.inventory_account
		or item.get("default_inventory_account")
		or item_group.get("default_inventory_account")
		or brand.get("default_inventory_account")
	)


def get_default_expense_account(ctx: ItemDetailsCtx, item, item_group, brand):
	if ctx.get("doctype") in ["Sales Invoice", "Delivery Note"]:
		expense_account = (
			item.get("default_cogs_account")
			or item_group.get("default_cogs_account")
			or brand.get("default_cogs_account")
		)

		if not expense_account:
			expense_account = frappe.get_cached_value("Company", ctx.company, "default_expense_account")

		if expense_account:
			return expense_account

	return (
		item.get("expense_account")
		or item_group.get("expense_account")
		or brand.get("expense_account")
		or ctx.expense_account
	)


def get_provisional_account(ctx: ItemDetailsCtx, item, item_group, brand):
	return (
		item.get("default_provisional_account")
		or item_group.get("default_provisional_account")
		or brand.get("default_provisional_account")
		or ctx.default_provisional_account
	)


def get_default_discount_account(ctx: ItemDetailsCtx, item, item_group, brand):
	return (
		item.get("default_discount_account")
		or item_group.get("default_discount_account")
		or brand.get("default_discount_account")
		or ctx.discount_account
	)


def get_default_deferred_account(ctx: ItemDetailsCtx, item, fieldname=None):
	if item.get("enable_deferred_revenue") or item.get("enable_deferred_expense"):
		return (
			frappe.get_cached_value(
				"Item Default",
				{"parent": ctx.item_code, "company": ctx.company},
				fieldname,
			)
			or ctx.get(fieldname)
			or frappe.get_cached_value("Company", ctx.company, "default_" + fieldname)
		)
	else:
		return None


@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_default_cost_center(ctx: ItemDetailsCtx, item=None, item_group=None, brand=None, company=None):
	cost_center = None

	if not company and ctx.get("company"):
		company = ctx.get("company")

	if ctx.get("project"):
		cost_center = frappe.db.get_value("Project", ctx.get("project"), "cost_center", cache=True)

	if not cost_center and (item and item_group and brand):
		if ctx.get("customer"):
			cost_center = (
				item.get("selling_cost_center")
				or item_group.get("selling_cost_center")
				or brand.get("selling_cost_center")
			)
		else:
			cost_center = (
				item.get("buying_cost_center")
				or item_group.get("buying_cost_center")
				or brand.get("buying_cost_center")
			)

	elif not cost_center and ctx.get("item_code") and company:
		for method in ["get_item_defaults", "get_item_group_defaults", "get_brand_defaults"]:
			path = f"erpnext.stock.get_item_details.{method}"
			data = frappe.get_attr(path)(ctx.get("item_code"), company)

			if data and (data.selling_cost_center or data.buying_cost_center):
				if ctx.get("customer") and data.selling_cost_center:
					return data.selling_cost_center

				elif ctx.get("supplier") and data.buying_cost_center:
					return data.buying_cost_center

				return data.selling_cost_center or data.buying_cost_center

	if not cost_center and ctx.get("cost_center"):
		cost_center = ctx.get("cost_center")

	if company and cost_center and frappe.get_cached_value("Cost Center", cost_center, "company") != company:
		return None

	if not cost_center and company:
		cost_center = frappe.get_cached_value("Company", company, "cost_center")

	return cost_center


def get_default_supplier(_ctx: ItemDetailsCtx, item, item_group, brand):
	return item.get("default_supplier") or item_group.get("default_supplier") or brand.get("default_supplier")


def get_price_list_rate(ctx: ItemDetailsCtx, item_doc, out: ItemDetails = None):
	if out is None:
		out = ItemDetails()

	meta = frappe.get_meta(ctx.parenttype or ctx.doctype)

	if meta.get_field("currency") or ctx.get("currency"):
		if not ctx.price_list_currency or not ctx.plc_conversion_rate:
			# if currency and plc_conversion_rate exist then
			# `get_price_list_currency_and_exchange_rate` has already been called
			pl_details = get_price_list_currency_and_exchange_rate(ctx)
			ctx.update(pl_details)

		if meta.get_field("currency"):
			validate_conversion_rate(ctx, meta)

		price_list_rate = get_price_list_rate_for(ctx, item_doc.name)

		# variant
		if price_list_rate is None and item_doc.variant_of:
			price_list_rate = get_price_list_rate_for(ctx, item_doc.variant_of)

		# insert in database
		if price_list_rate is None or frappe.get_cached_value(
			"Stock Settings", "Stock Settings", "update_existing_price_list_rate"
		):
			insert_item_price(ctx)

		if price_list_rate is None:
			return out

		out.price_list_rate = flt(price_list_rate) * flt(ctx.plc_conversion_rate) / flt(ctx.conversion_rate)

		if frappe.db.get_single_value("Buying Settings", "disable_last_purchase_rate"):
			return out

		if not ctx.is_internal_supplier and not out.price_list_rate and ctx.transaction_type == "buying":
			from erpnext.stock.doctype.item.item import get_last_purchase_details

			out.update(get_last_purchase_details(item_doc.name, ctx.name, ctx.conversion_rate))

	return out


def insert_item_price(ctx: ItemDetailsCtx):
	"""Insert Item Price if Price List and Price List Rate are specified and currency is the same"""
	if not ctx.price_list or not ctx.rate or ctx.is_internal_supplier or ctx.is_internal_customer:
		return

	stock_settings = frappe.get_cached_doc("Stock Settings")

	if (
		not frappe.db.get_value("Price List", ctx.price_list, "currency", cache=True) == ctx.currency
		or not stock_settings.auto_insert_price_list_rate_if_missing
		or not frappe.has_permission("Item Price", "write")
	):
		return

	item_price = frappe.db.get_value(
		"Item Price",
		{
			"item_code": ctx.item_code,
			"price_list": ctx.price_list,
			"currency": ctx.currency,
			"uom": ctx.stock_uom,
		},
		["name", "price_list_rate"],
		as_dict=1,
	)

	update_based_on_price_list_rate = stock_settings.update_price_list_based_on == "Price List Rate"

	if item_price and item_price.name:
		if not stock_settings.update_existing_price_list_rate:
			return

		rate_to_consider = flt(ctx.price_list_rate) if update_based_on_price_list_rate else flt(ctx.rate)
		price_list_rate = _get_stock_uom_rate(rate_to_consider, ctx)

		if not price_list_rate or item_price.price_list_rate == price_list_rate:
			return

		frappe.db.set_value("Item Price", item_price.name, "price_list_rate", price_list_rate)
		frappe.msgprint(
			_("Item Price updated for {0} in Price List {1}").format(ctx.item_code, ctx.price_list),
			alert=True,
		)
	else:
		rate_to_consider = (
			(flt(ctx.price_list_rate) or flt(ctx.rate)) if update_based_on_price_list_rate else flt(ctx.rate)
		)
		price_list_rate = _get_stock_uom_rate(rate_to_consider, ctx)

		item_price = frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": ctx.price_list,
				"item_code": ctx.item_code,
				"currency": ctx.currency,
				"price_list_rate": price_list_rate,
				"uom": ctx.stock_uom,
			}
		)
		item_price.insert()
		frappe.msgprint(
			_("Item Price added for {0} in Price List {1}").format(ctx.item_code, ctx.price_list),
			alert=True,
		)


def _get_stock_uom_rate(rate: float, ctx: ItemDetailsCtx):
	return rate / ctx.conversion_factor if ctx.conversion_factor else rate


def get_item_price(
	pctx: ItemPriceCtx | dict, item_code, ignore_party=False, force_batch_no=False
) -> list[dict]:
	"""
	Get name, price_list_rate from Item Price based on conditions
	        Check if the desired qty is within the increment of the packing list.
	:param pctx: dict (or frappe._dict) with mandatory fields price_list, uom
	        optional fields transaction_date, customer, supplier
	:param item_code: str, Item Doctype field item_code
	"""
	pctx: ItemPriceCtx = frappe._dict(pctx)

	ip = frappe.qb.DocType("Item Price")
	query = (
		frappe.qb.from_(ip)
		.select(ip.name, ip.price_list_rate, ip.uom)
		.where(
			(ip.item_code == item_code)
			& (ip.price_list == pctx.price_list)
			& (IfNull(ip.uom, "").isin(["", pctx.uom]))
		)
		.orderby(ip.valid_from, order=frappe.qb.desc)
		.orderby(IfNull(ip.batch_no, ""), order=frappe.qb.desc)
		.orderby(ip.uom, order=frappe.qb.desc)
		.limit(1)
	)

	if force_batch_no:
		query = query.where(ip.batch_no == pctx.batch_no)
	else:
		query = query.where(IfNull(ip.batch_no, "").isin(["", pctx.batch_no]))

	if not ignore_party:
		if pctx.customer:
			query = query.where(ip.customer == pctx.customer)
		elif pctx.supplier:
			query = query.where(ip.supplier == pctx.supplier)
		else:
			query = query.where((IfNull(ip.customer, "") == "") & (IfNull(ip.supplier, "") == ""))

	if pctx.transaction_date:
		query = query.where(
			(IfNull(ip.valid_from, "2000-01-01") <= pctx.transaction_date)
			& (IfNull(ip.valid_upto, "2500-12-31") >= pctx.transaction_date)
		)

	return query.run(as_dict=True)


@frappe.whitelist()
def get_batch_based_item_price(pctx: ItemPriceCtx | dict | str, item_code) -> float:
	pctx = parse_json(pctx)

	item_price = get_item_price(pctx, item_code, force_batch_no=True)
	if not item_price:
		item_price = get_item_price(pctx, item_code, ignore_party=True, force_batch_no=True)

	is_free_item = pctx.get("items", [{}])[0].get("is_free_item")

	if item_price and item_price[0].uom == pctx.uom and not is_free_item:
		return item_price[0].price_list_rate

	return 0.0


@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_price_list_rate_for(ctx: ItemDetailsCtx, item_code):
	"""
	:param customer: link to Customer DocType
	:param supplier: link to Supplier DocType
	:param price_list: str (Standard Buying or Standard Selling)
	:param item_code: str, Item Doctype field item_code
	:param qty: Desired Qty
	:param transaction_date: Date of the price
	"""
	pctx = ItemPriceCtx(
		{
			"item_code": item_code,
			"price_list": ctx.get("price_list"),
			"customer": ctx.get("customer"),
			"supplier": ctx.get("supplier"),
			"uom": ctx.get("uom"),
			"transaction_date": ctx.get("transaction_date"),
			"batch_no": ctx.get("batch_no"),
		}
	)

	item_price_data = 0
	price_list_rate = get_item_price(pctx, item_code)
	if price_list_rate:
		desired_qty = ctx.get("qty")
		if desired_qty and check_packing_list(price_list_rate[0].name, desired_qty, item_code):
			item_price_data = price_list_rate
	else:
		for field in ["customer", "supplier"]:
			del pctx[field]

		general_price_list_rate = get_item_price(pctx, item_code, ignore_party=ctx.get("ignore_party"))

		if not general_price_list_rate and ctx.get("uom") != ctx.get("stock_uom"):
			pctx.uom = ctx.get("stock_uom")
			general_price_list_rate = get_item_price(pctx, item_code, ignore_party=ctx.get("ignore_party"))

		if general_price_list_rate:
			item_price_data = general_price_list_rate

	if item_price_data:
		if item_price_data[0].uom == ctx.get("uom"):
			return item_price_data[0].price_list_rate
		elif not ctx.get("price_list_uom_dependant"):
			return flt(item_price_data[0].price_list_rate * flt(ctx.get("conversion_factor", 1)))
		else:
			return item_price_data[0].price_list_rate


def check_packing_list(price_list_rate_name, desired_qty, item_code):
	"""
	Check if the desired qty is within the increment of the packing list.
	:param price_list_rate_name: Name of Item Price
	:param desired_qty: Desired Qt
	:param item_code: str, Item Doctype field item_code
	:param qty: Desired Qt
	"""

	flag = True
	if packing_unit := frappe.db.get_value("Item Price", price_list_rate_name, "packing_unit", cache=True):
		packing_increment = desired_qty % packing_unit

		if packing_increment != 0:
			flag = False

	return flag


def validate_conversion_rate(ctx: ItemDetailsCtx, meta):
	from erpnext.controllers.accounts_controller import validate_conversion_rate

	company_currency = frappe.get_cached_value("Company", ctx.company, "default_currency")
	if not ctx.conversion_rate and ctx.currency == company_currency:
		ctx.conversion_rate = 1.0

	if not ctx.ignore_conversion_rate and ctx.conversion_rate == 1 and ctx.currency != company_currency:
		ctx.conversion_rate = (
			get_exchange_rate(ctx.currency, company_currency, ctx.transaction_date, "for_buying") or 1.0
		)

	# validate currency conversion rate
	validate_conversion_rate(
		ctx.currency, ctx.conversion_rate, meta.get_label("conversion_rate"), ctx.company
	)

	ctx.conversion_rate = flt(
		ctx.conversion_rate,
		get_field_precision(meta.get_field("conversion_rate"), frappe._dict({"fields": ctx})),
	)

	if ctx.price_list:
		if not ctx.plc_conversion_rate and ctx.price_list_currency == frappe.db.get_value(
			"Price List", ctx.price_list, "currency", cache=True
		):
			ctx.plc_conversion_rate = 1.0

		# validate price list currency conversion rate
		if not ctx.price_list_currency:
			throw(_("Price List Currency not selected"))
		else:
			validate_conversion_rate(
				ctx.price_list_currency,
				ctx.plc_conversion_rate,
				meta.get_label("plc_conversion_rate"),
				ctx.company,
			)

			if meta.get_field("plc_conversion_rate"):
				ctx.plc_conversion_rate = flt(
					ctx.plc_conversion_rate,
					get_field_precision(meta.get_field("plc_conversion_rate"), frappe._dict({"fields": ctx})),
				)


def get_party_item_code(ctx: ItemDetailsCtx, item_doc, out: ItemDetails):
	if ctx.transaction_type == "selling" and ctx.customer:
		out.customer_item_code = None

		if ctx.quotation_to and ctx.quotation_to != "Customer":
			return

		customer_item_code = item_doc.get("customer_items", {"customer_name": ctx.customer})

		if customer_item_code:
			out.customer_item_code = customer_item_code[0].ref_code
		else:
			customer_group = frappe.get_cached_value("Customer", ctx.customer, "customer_group")
			customer_group_item_code = item_doc.get("customer_items", {"customer_group": customer_group})
			if customer_group_item_code and not customer_group_item_code[0].customer_name:
				out.customer_item_code = customer_group_item_code[0].ref_code

	if ctx.transaction_type == "buying" and ctx.supplier:
		item_supplier = item_doc.get("supplier_items", {"supplier": ctx.supplier})
		out.supplier_part_no = item_supplier[0].supplier_part_no if item_supplier else None


from erpnext.deprecation_dumpster import get_pos_profile_item_details


@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_pos_profile_item_details_(ctx: ItemDetailsCtx, company, pos_profile=None, update_data=False):
	res = frappe._dict()

	if not frappe.flags.pos_profile and not pos_profile:
		pos_profile = frappe.flags.pos_profile = get_pos_profile(company, ctx.pos_profile)

	if pos_profile:
		for fieldname in ("income_account", "cost_center", "warehouse", "expense_account"):
			if (not ctx.get(fieldname) or update_data) and pos_profile.get(fieldname):
				res[fieldname] = pos_profile.get(fieldname)

		if res.get("warehouse"):
			res.actual_qty = get_bin_details(ctx.item_code, res.warehouse, include_child_warehouses=True).get(
				"actual_qty"
			)

	return res


@frappe.whitelist()
def get_pos_profile(company, pos_profile=None, user=None):
	if pos_profile:
		return frappe.get_cached_doc("POS Profile", pos_profile)

	if not user:
		user = frappe.session["user"]

	pf = frappe.qb.DocType("POS Profile")
	pfu = frappe.qb.DocType("POS Profile User")

	query = (
		frappe.qb.from_(pf)
		.left_join(pfu)
		.on(pf.name == pfu.parent)
		.select(pf.star)
		.where((pfu.user == user) & (pfu.default == 1))
	)

	if company:
		query = query.where(pf.company == company)

	pos_profile = query.run(as_dict=True)

	if not pos_profile and company:
		pos_profile = (
			frappe.qb.from_(pf)
			.left_join(pfu)
			.on(pf.name == pfu.parent)
			.select(pf.star)
			.where((pf.company == company) & (pf.disabled == 0))
		).run(as_dict=True)

	return pos_profile and pos_profile[0] or None


@frappe.whitelist()
def get_conversion_factor(item_code, uom):
	item = frappe.get_cached_value("Item", item_code, ["variant_of", "stock_uom"], as_dict=True)
	if not item_code or not item or uom == item.stock_uom:
		return {"conversion_factor": 1.0}

	item_codes = [item_code]
	if item.variant_of:
		item_codes.append(item.variant_of)

	parent = frappe.qb.DocType("Item")
	child = frappe.qb.DocType("UOM Conversion Detail")
	query = (
		frappe.qb.from_(parent)
		.join(child)
		.on(parent.name == child.parent)
		.select(child.conversion_factor)
		.where((parent.name.isin(item_codes)) & (child.uom == uom))
		.orderby(parent.has_variants)
		.limit(1)
	)
	conversion_factor = query.run(pluck="conversion_factor")

	if not conversion_factor:
		conversion_factor = get_uom_conv_factor(uom, item.stock_uom)
	else:
		conversion_factor = conversion_factor[0]

	return {"conversion_factor": conversion_factor or 1.0}


@frappe.whitelist()
def get_projected_qty(item_code, warehouse):
	return {
		"projected_qty": frappe.db.get_value(
			"Bin", {"item_code": item_code, "warehouse": warehouse}, "projected_qty"
		)
	}


@frappe.whitelist()
def get_bin_details(item_code, warehouse, company=None, include_child_warehouses=False):
	bin_details = {"projected_qty": 0, "actual_qty": 0, "reserved_qty": 0}

	if warehouse:
		from frappe.query_builder.functions import Coalesce, Sum

		from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses

		warehouses = get_child_warehouses(warehouse) if include_child_warehouses else [warehouse]

		bin = frappe.qb.DocType("Bin")
		bin_details = (
			frappe.qb.from_(bin)
			.select(
				Coalesce(Sum(bin.projected_qty), 0).as_("projected_qty"),
				Coalesce(Sum(bin.actual_qty), 0).as_("actual_qty"),
				Coalesce(Sum(bin.reserved_qty), 0).as_("reserved_qty"),
			)
			.where((bin.item_code == item_code) & (bin.warehouse.isin(warehouses)))
		).run(as_dict=True)[0]

	if company:
		bin_details["company_total_stock"] = get_company_total_stock(item_code, company)

	return bin_details


def get_company_total_stock(item_code, company):
	bin = frappe.qb.DocType("Bin")
	wh = frappe.qb.DocType("Warehouse")

	return (
		frappe.qb.from_(bin)
		.inner_join(wh)
		.on(bin.warehouse == wh.name)
		.select(Sum(bin.actual_qty))
		.where((wh.company == company) & (bin.item_code == item_code))
	).run()[0][0]


@frappe.whitelist()
def get_batch_qty(batch_no, warehouse, item_code):
	from erpnext.stock.doctype.batch import batch

	if batch_no:
		return {"actual_batch_qty": batch.get_batch_qty(batch_no, warehouse)}


@frappe.whitelist()
@erpnext.normalize_ctx_input(ItemDetailsCtx)
def apply_price_list(ctx: ItemDetailsCtx, as_doc=False, doc=None):
	"""Apply pricelist on a document-like dict object and return as
	{'parent': dict, 'children': list}

	:param ctx: See below
	:param as_doc: Updates value in the passed dict

	        ctx = {
	                "doctype": "",
	                "name": "",
	                "items": [{"doctype": "", "name": "", "item_code": "", "brand": "", "item_group": ""}, ...],
	                "conversion_rate": 1.0,
	                "selling_price_list": None,
	                "price_list_currency": None,
	                "price_list_uom_dependant": None,
	                "plc_conversion_rate": 1.0,
	                "doctype": "",
	                "name": "",
	                "supplier": None,
	                "transaction_date": None,
	                "conversion_rate": 1.0,
	                "buying_price_list": None,
	                "ignore_pricing_rule": 0/1
	        }
	"""
	_preprocess_ctx(ctx)
	parent = get_price_list_currency_and_exchange_rate(ctx)
	ctx.update(parent)

	children = []

	if "items" in ctx:
		item_list = ctx.get("items")
		ctx.update(parent)

		for item in item_list:
			ctx_copy = ItemDetailsCtx(ctx.copy())
			ctx_copy.update(item)
			item_details = apply_price_list_on_item(ctx_copy, doc=doc)
			children.append(item_details)

	if as_doc:
		ctx.price_list_currency = (parent.price_list_currency,)
		ctx.plc_conversion_rate = parent.plc_conversion_rate
		if ctx.get("items"):
			for i, item in enumerate(ctx.get("items")):
				for fieldname in children[i]:
					# if the field exists in the original doc
					# update the value
					if fieldname in item and fieldname not in ("name", "doctype"):
						item[fieldname] = children[i][fieldname]
		return ctx
	else:
		return {"parent": parent, "children": children}


def apply_price_list_on_item(ctx, doc=None):
	item_doc = frappe.get_cached_doc("Item", ctx.item_code)
	item_details = get_price_list_rate(ctx, item_doc)
	item_details.update(get_pricing_rule_for_item(ctx, doc=doc))

	return item_details


def get_price_list_currency_and_exchange_rate(ctx: ItemDetailsCtx):
	if not ctx.price_list:
		return {}

	if ctx.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
		ctx.update({"exchange_rate": "for_selling"})
	elif ctx.doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
		ctx.update({"exchange_rate": "for_buying"})

	price_list_details = get_price_list_details(ctx.price_list)

	price_list_currency = price_list_details.get("currency")
	price_list_uom_dependant = price_list_details.get("price_list_uom_dependant")

	plc_conversion_rate = ctx.plc_conversion_rate
	company_currency = get_company_currency(ctx.company)

	if (not plc_conversion_rate) or (
		price_list_currency and ctx.price_list_currency and price_list_currency != ctx.price_list_currency
	):
		# cksgb 19/09/2016: added args.transaction_date as posting_date argument for get_exchange_rate
		plc_conversion_rate = (
			get_exchange_rate(price_list_currency, company_currency, ctx.transaction_date, ctx.exchange_rate)
			or plc_conversion_rate
		)

	return frappe._dict(
		{
			"price_list_currency": price_list_currency,
			"price_list_uom_dependant": price_list_uom_dependant,
			"plc_conversion_rate": plc_conversion_rate or 1,
		}
	)


@frappe.whitelist()
def get_default_bom(item_code=None):
	def _get_bom(item):
		bom = frappe.get_all("BOM", dict(item=item, is_active=True, is_default=True, docstatus=1), limit=1)
		return bom[0].name if bom else None

	if not item_code:
		return

	bom_name = _get_bom(item_code)

	template_item = frappe.db.get_value("Item", item_code, "variant_of")
	if not bom_name and template_item:
		bom_name = _get_bom(template_item)

	return bom_name


@frappe.whitelist()
def get_valuation_rate(item_code, company, warehouse=None):
	if frappe.get_cached_value("Warehouse", warehouse, "is_group"):
		return {"valuation_rate": 0.0}

	item = get_item_defaults(item_code, company)
	item_group = get_item_group_defaults(item_code, company)
	brand = get_brand_defaults(item_code, company)
	if item.get("is_stock_item"):
		if not warehouse:
			warehouse = (
				item.get("default_warehouse")
				or item_group.get("default_warehouse")
				or brand.get("default_warehouse")
			)

		return frappe.db.get_value(
			"Bin", {"item_code": item_code, "warehouse": warehouse}, ["valuation_rate"], as_dict=True
		) or {"valuation_rate": item.get("valuation_rate") or 0}

	elif not item.get("is_stock_item"):
		pi_item = frappe.qb.DocType("Purchase Invoice Item")
		valuation_rate = (
			frappe.qb.from_(pi_item)
			.select(Sum(pi_item.base_net_amount) / Sum(pi_item.qty * pi_item.conversion_factor))
			.where((pi_item.docstatus == 1) & (pi_item.item_code == item_code))
		).run()

		if valuation_rate:
			return {"valuation_rate": valuation_rate[0][0] or 0.0}
	else:
		return {"valuation_rate": 0.0}


def get_gross_profit(out: ItemDetails):
	if out.valuation_rate:
		out.update({"gross_profit": ((out.base_rate - out.valuation_rate) * out.stock_qty)})

	return out


@frappe.whitelist()
def get_serial_no(_args, serial_nos=None, sales_order=None):
	serial_nos = serial_nos or []
	return serial_nos


def update_party_blanket_order(ctx: ItemDetailsCtx, out: ItemDetails | dict):
	if out["against_blanket_order"]:
		blanket_order_details = get_blanket_order_details(ctx)
		if blanket_order_details:
			out.update(blanket_order_details)


@frappe.whitelist()
@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_blanket_order_details(ctx: ItemDetailsCtx):
	blanket_order_details = None

	if ctx.item_code:
		bo = frappe.qb.DocType("Blanket Order")
		bo_item = frappe.qb.DocType("Blanket Order Item")

		query = (
			frappe.qb.from_(bo)
			.from_(bo_item)
			.select(bo_item.rate.as_("blanket_order_rate"), bo.name.as_("blanket_order"))
			.where(
				(bo.company == ctx.company)
				& (bo_item.item_code == ctx.item_code)
				& (bo.docstatus == 1)
				& (bo.name == bo_item.parent)
			)
		)

		if ctx.customer and ctx.doctype == "Sales Order":
			query = query.where(bo.customer == ctx.customer)
		elif ctx.supplier and ctx.doctype == "Purchase Order":
			query = query.where(bo.supplier == ctx.supplier)
		if ctx.blanket_order:
			query = query.where(bo.name == ctx.blanket_order)
		if ctx.transaction_date:
			query = query.where(bo.to_date >= ctx.transaction_date)

		blanket_order_details = query.run(as_dict=True)
		blanket_order_details = blanket_order_details[0] if blanket_order_details else ""

	return blanket_order_details
