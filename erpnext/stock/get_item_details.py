# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, throw
from frappe.utils import flt, cint, add_days
import json
from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item
from erpnext.setup.utils import get_exchange_rate

@frappe.whitelist()
def get_item_details(args):
	"""
		args = {
			"item_code": "",
			"warehouse": None,
			"customer": "",
			"conversion_rate": 1.0,
			"selling_price_list": None,
			"price_list_currency": None,
			"plc_conversion_rate": 1.0,
			"parenttype": "",
			"parent": "",
			"supplier": None,
			"transaction_date": None,
			"conversion_rate": 1.0,
			"buying_price_list": None,
			"is_subcontracted": "Yes" / "No",
			"transaction_type": "selling",
			"ignore_pricing_rule": 0/1
		}
	"""
	args = process_args(args)
	item_doc = frappe.get_doc("Item", args.item_code)
	item = item_doc


	validate_item_details(args, item)

	out = get_basic_details(args, item_doc)

	get_party_item_code(args, item_doc, out)

	if out.get("warehouse"):
		out.update(get_available_qty(args.item_code, out.warehouse))
		out.update(get_projected_qty(item.name, out.warehouse))

	get_price_list_rate(args, item_doc, out)

	if args.transaction_type == "selling" and cint(args.is_pos):
		out.update(get_pos_settings_item_details(args.company, args))

	# update args with out, if key or value not exists
	for key, value in out.iteritems():
		if args.get(key) is None:
			args[key] = value

	out.update(get_pricing_rule_for_item(args))

	if args.get("parenttype") in ("Sales Invoice", "Delivery Note"):
		if item_doc.has_serial_no == "Yes" and not args.serial_no:
			out.serial_no = get_serial_nos_by_fifo(args, item_doc)

	if args.transaction_date and item.lead_time_days:
		out.schedule_date = out.lead_time_date = add_days(args.transaction_date,
			item.lead_time_days)

	return out

def process_args(args):
	if isinstance(args, basestring):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.get("transaction_type"):
		if args.get("parenttype")=="Material Request" or \
				frappe.get_meta(args.get("parenttype")).get_field("supplier"):
			args.transaction_type = "buying"
		else:
			args.transaction_type = "selling"

	if not args.get("price_list"):
		args.price_list = args.get("selling_price_list") or args.get("buying_price_list")

	if args.barcode:
		args.item_code = get_item_code(barcode=args.barcode)
	elif not args.item_code and args.serial_no:
		args.item_code = get_item_code(serial_no=args.serial_no)

	return args

def get_item_code(barcode=None, serial_no=None):
	if barcode:
		item_code = frappe.db.get_value("Item", {"barcode": barcode})
		if not item_code:
			frappe.throw(_("No Item with Barcode {0}").format(barcode))
	elif serial_no:
		item_code = frappe.db.get_value("Serial No", serial_no, "item_code")
		if not item_code:
			frappe.throw(_("No Item with Serial No {0}").format(serial_no))

	return item_code

def validate_item_details(args, item):
	if not args.company:
		throw(_("Please specify Company"))

	from erpnext.stock.doctype.item.item import validate_end_of_life
	validate_end_of_life(item.name, item.end_of_life)

	if args.transaction_type == "selling":
		# validate if sales item or service item
		if args.get("order_type") == "Maintenance":
			if item.is_service_item != "Yes":
				throw(_("Item {0} must be a Service Item.").format(item.name))

		elif item.is_sales_item != "Yes":
			throw(_("Item {0} must be a Sales Item").format(item.name))

	elif args.transaction_type == "buying" and args.parenttype != "Material Request":
		# validate if purchase item or subcontracted item
		if item.is_purchase_item != "Yes":
			throw(_("Item {0} must be a Purchase Item").format(item.name))

		if args.get("is_subcontracted") == "Yes" and item.is_sub_contracted_item != "Yes":
			throw(_("Item {0} must be a Sub-contracted Item").format(item.name))

def get_basic_details(args, item_doc):
	item = item_doc

	from frappe.defaults import get_user_default_as_list
	user_default_warehouse_list = get_user_default_as_list('warehouse')
	user_default_warehouse = user_default_warehouse_list[0] \
		if len(user_default_warehouse_list)==1 else ""

	out = frappe._dict({

		"item_code": item.name,
		"item_name": item.item_name,
		"description": item.description_html or item.description,
		"warehouse": user_default_warehouse or args.warehouse or item.default_warehouse,
		"income_account": (item.income_account
			or args.income_account
			or frappe.db.get_value("Item Group", item.item_group, "default_income_account")
			or frappe.db.get_value("Company", args.company, "default_income_account")),
		"expense_account": (item.expense_account
			or args.expense_account
			or frappe.db.get_value("Item Group", item.item_group, "default_expense_account")
			or frappe.db.get_value("Company", args.company, "default_expense_account")),
		"cost_center": ((item.selling_cost_center if args.transaction_type == "selling" else item.buying_cost_center)
			or frappe.db.get_value("Item Group", item.item_group, "default_cost_center")
			or frappe.db.get_value("Company", args.company, "cost_center")),
		"batch_no": None,
		"item_tax_rate": json.dumps(dict(([d.tax_type, d.tax_rate] for d in
			item_doc.get("item_tax")))),
		"uom": item.stock_uom,
		"min_order_qty": flt(item.min_order_qty) if args.parenttype == "Material Request" else "",
		"conversion_factor": 1.0,
		"qty": 1.0,
		"stock_qty": 1.0,
		"price_list_rate": 0.0,
		"base_price_list_rate": 0.0,
		"rate": 0.0,
		"base_rate": 0.0,
		"amount": 0.0,
		"base_amount": 0.0,
		"discount_percentage": 0.0
	})

	for fieldname in ("item_name", "item_group", "barcode", "brand", "stock_uom"):
		out[fieldname] = item.get(fieldname)

	return out

def get_price_list_rate(args, item_doc, out):
	meta = frappe.get_meta(args.parenttype)

	if meta.get_field("currency"):
		validate_price_list(args)
		validate_conversion_rate(args, meta)


		price_list_rate = frappe.db.get_value("Item Price",
			{"price_list": args.price_list, "item_code": args.item_code}, "price_list_rate")

		if not price_list_rate: return {}

		out.price_list_rate = flt(price_list_rate) * flt(args.plc_conversion_rate) \
			/ flt(args.conversion_rate)

		if not out.price_list_rate and args.transaction_type == "buying":
			from erpnext.stock.doctype.item.item import get_last_purchase_details
			out.update(get_last_purchase_details(item_doc.name,
				args.parent, args.conversion_rate))

def validate_price_list(args):
	if args.get("price_list"):
		if not frappe.db.get_value("Price List",
			{"name": args.price_list, args.transaction_type: 1, "enabled": 1}):
			throw(_("Price List {0} is disabled").format(args.price_list))
	else:
		throw(_("Price List not selected"))

def validate_conversion_rate(args, meta):
	from erpnext.setup.doctype.currency.currency import validate_conversion_rate
	from frappe.model.meta import get_field_precision

	# validate currency conversion rate
	validate_conversion_rate(args.currency, args.conversion_rate,
		meta.get_label("conversion_rate"), args.company)

	args.conversion_rate = flt(args.conversion_rate,
		get_field_precision(meta.get_field("conversion_rate"),
			frappe._dict({"fields": args})))

	# validate price list currency conversion rate
	if not args.get("price_list_currency"):
		throw(_("Price List Currency not selected"))
	else:
		validate_conversion_rate(args.price_list_currency, args.plc_conversion_rate,
			meta.get_label("plc_conversion_rate"), args.company)

		args.plc_conversion_rate = flt(args.plc_conversion_rate,
			get_field_precision(meta.get_field("plc_conversion_rate"),
			frappe._dict({"fields": args})))

def get_party_item_code(args, item_doc, out):
	if args.transaction_type == "selling":
		customer_item_code = item_doc.get("item_customer_details", {"customer_name": args.customer})
		out.customer_item_code = customer_item_code[0].ref_code if customer_item_code else None
	else:
		item_supplier = item_doc.get("item_supplier_details", {"supplier": args.supplier})
		out.supplier_part_no = item_supplier[0].supplier_part_no if item_supplier else None


def get_pos_settings_item_details(company, args, pos_settings=None):
	res = frappe._dict()

	if not pos_settings:
		pos_settings = get_pos_settings(company)

	if pos_settings:
		for fieldname in ("income_account", "cost_center", "warehouse", "expense_account"):
			if not args.get(fieldname) and pos_settings.get(fieldname):
				res[fieldname] = pos_settings.get(fieldname)

		if res.get("warehouse"):
			res.actual_qty = get_available_qty(args.item_code,
				res.warehouse).get("actual_qty")

	return res

def get_pos_settings(company):
	pos_settings = frappe.db.sql("""select * from `tabPOS Setting` where user = %s
		and company = %s""", (frappe.session['user'], company), as_dict=1)

	if not pos_settings:
		pos_settings = frappe.db.sql("""select * from `tabPOS Setting`
			where ifnull(user,'') = '' and company = %s""", company, as_dict=1)

	return pos_settings and pos_settings[0] or None


def get_serial_nos_by_fifo(args, item_doc):
	return "\n".join(frappe.db.sql_list("""select name from `tabSerial No`
		where item_code=%(item_code)s and warehouse=%(warehouse)s and status='Available'
		order by timestamp(purchase_date, purchase_time) asc limit %(qty)s""", {
			"item_code": args.item_code,
			"warehouse": args.warehouse,
			"qty": cint(args.qty)
		}))

@frappe.whitelist()
def get_conversion_factor(item_code, uom):
	return {"conversion_factor": frappe.db.get_value("UOM Conversion Detail",
		{"parent": item_code, "uom": uom}, "conversion_factor")}

@frappe.whitelist()
def get_projected_qty(item_code, warehouse):
	return {"projected_qty": frappe.db.get_value("Bin",
		{"item_code": item_code, "warehouse": warehouse}, "projected_qty")}

@frappe.whitelist()
def get_available_qty(item_code, warehouse):
	return frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse},
		["projected_qty", "actual_qty"], as_dict=True) or {}

@frappe.whitelist()
def apply_price_list(args):
	"""
		args = {
			"item_list": [{"doctype": "", "name": "", "item_code": "", "brand": "", "item_group": ""}, ...],
			"conversion_rate": 1.0,
			"selling_price_list": None,
			"price_list_currency": None,
			"plc_conversion_rate": 1.0,
			"parenttype": "",
			"parent": "",
			"supplier": None,
			"transaction_date": None,
			"conversion_rate": 1.0,
			"buying_price_list": None,
			"transaction_type": "selling",
			"ignore_pricing_rule": 0/1
		}
	"""
	args = process_args(args)

	parent = get_price_list_currency_and_exchange_rate(args)
	children = []

	if "item_list" in args:
		item_list = args.get("item_list")
		del args["item_list"]

		args.update(parent)

		for item in item_list:
			args_copy = frappe._dict(args.copy())
			args_copy.update(item)
			item_details = apply_price_list_on_item(args_copy)
			children.append(item_details)

	return {
		"parent": parent,
		"children": children
	}

def apply_price_list_on_item(args):
	item_details = frappe._dict()
	item_doc = frappe.get_doc("Item", args.item_code)
	get_price_list_rate(args, item_doc, item_details)
	item_details.discount_percentage = 0.0
	item_details.update(get_pricing_rule_for_item(args))
	return item_details

def get_price_list_currency(price_list):
	result = frappe.db.get_value("Price List", {"name": price_list,
		"enabled": 1}, ["name", "currency"], as_dict=True)

	if not result:
		throw(_("Price List {0} is disabled").format(price_list))

	return result.currency

def get_price_list_currency_and_exchange_rate(args):
	price_list_currency = get_price_list_currency(args.price_list)
	plc_conversion_rate = args.plc_conversion_rate

	if (not plc_conversion_rate) or (price_list_currency != args.price_list_currency):
		plc_conversion_rate = get_exchange_rate(price_list_currency, args.currency) \
			or plc_conversion_rate

	return {
		"price_list_currency": price_list_currency,
		"plc_conversion_rate": plc_conversion_rate
	}
