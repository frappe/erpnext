# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, throw
from frappe.utils import flt, cint, add_days
from frappe.model.meta import has_field
import json

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
			"doctype": "",
			"docname": "",
			"supplier": None,
			"transaction_date": None,
			"conversion_rate": 1.0,
			"buying_price_list": None,
			"is_subcontracted": "Yes" / "No",
			"transaction_type": "selling"
		}
	"""

	if isinstance(args, basestring):
		args = json.loads(args)
	args = frappe._dict(args)

	if not args.get("transaction_type"):
		args.transaction_type = "buying" if has_field(args.get("doctype"), "supplier") \
			else "selling"
		
	if not args.get("price_list"):
		args.price_list = args.get("selling_price_list") or args.get("buying_price_list")
	
	if args.barcode:
		args.item_code = get_item_code(barcode=args.barcode)
	elif not args.item_code and args.serial_no:
		args.item_code = get_item_code(serial_no=args.serial_no)
	
	item_bean = frappe.bean("Item", args.item_code)
	item = item_bean.doc

	validate_item_details(args, item)
		
	out = get_basic_details(args, item_bean)
	
	get_party_item_code(args, item_bean, out)

	if out.get("warehouse"):
		out.update(get_available_qty(args.item_code, out.warehouse))
		out.update(get_projected_qty(item.name, out.warehouse))
	
	get_price_list_rate(args, item_bean, out)

	if args.transaction_type == "selling" and cint(args.is_pos):
		out.update(get_pos_settings_item_details(args.company, args))
	
	apply_pricing_rule(out, args)
		
	if args.get("doctype") in ("Sales Invoice", "Delivery Note"):
		if item_bean.doc.has_serial_no == "Yes" and not args.serial_no:
			out.serial_no = get_serial_nos_by_fifo(args, item_bean)
			
	if args.transaction_date and item.lead_time_days:
		out.schedule_date = out.lead_time_date = add_days(args.transaction_date,
			item.lead_time_days)
	
	return out

def get_item_code(barcode=None, serial_no=None):
	if barcode:
		item_code = frappe.db.get_value("Item", {"barcode": barcode})
	elif serial_no:
		item_code = frappe.db.get_value("Serial No", serial_no, "item_code")

	if not item_code:
		throw(_("No Item found with ") + _("Barcode") if barcode else _("Serial No") + 
			": %s" % (barcode or serial_no))
	
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
				throw(_("Item") + (" %s: " % item.name) + 
					_("is not a service item.") +
					_("Please select a service item or change the order type to Sales."))
		
		elif item.is_sales_item != "Yes":
			throw(_("Item") + (" %s: " % item.name) + _("is not a sales item"))

	elif args.transaction_type == "buying":
		# validate if purchase item or subcontracted item
		if item.is_purchase_item != "Yes":
			throw(_("Item") + (" %s: " % item.name) + _("is not a purchase item"))
	
		if args.get("is_subcontracted") == "Yes" and item.is_sub_contracted_item != "Yes":
			throw(_("Item") + (" %s: " % item.name) + 
				_("not a sub-contracted item.") +
				_("Please select a sub-contracted item or do not sub-contract the transaction."))
			
def get_basic_details(args, item_bean):
	item = item_bean.doc
	
	from frappe.defaults import get_user_default_as_list
	user_default_warehouse_list = get_user_default_as_list('warehouse')
	user_default_warehouse = user_default_warehouse_list[0] \
		if len(user_default_warehouse_list)==1 else ""

	out = frappe._dict({
		"item_code": item.name,
		"item_name": item.item_name,
		"description": item.description_html or item.description,
		"warehouse": user_default_warehouse or args.warehouse or item.default_warehouse,
		"income_account": item.income_account or args.income_account \
			or frappe.db.get_value("Company", args.company, "default_income_account"),
		"expense_account": item.expense_account or args.expense_account \
			or frappe.db.get_value("Company", args.company, "default_expense_account"),
		"cost_center": item.selling_cost_center \
			if args.transaction_type == "selling" else item.buying_cost_center,
		"batch_no": None,
		"item_tax_rate": json.dumps(dict(([d.tax_type, d.tax_rate] for d in 
			item_bean.doclist.get({"parentfield": "item_tax"})))),
		"uom": item.stock_uom,
		"min_order_qty": flt(item.min_order_qty) if args.doctype == "Material Request" else "",
		"conversion_factor": 1.0,
		"qty": 1.0,
		"price_list_rate": 0.0,
		"base_price_list_rate": 0.0,
		"rate": 0.0,
		"base_rate": 0.0,
		"amount": 0.0,
		"base_amount": 0.0,
		"discount_percentage": 0.0
	})
	
	for fieldname in ("item_name", "item_group", "barcode", "brand", "stock_uom"):
		out[fieldname] = item.fields.get(fieldname)
			
	return out
	
def get_price_list_rate(args, item_bean, out):
	meta = frappe.get_doctype(args.doctype)

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
			out.update(get_last_purchase_details(item_bean.doc.name, 
				args.docname, args.conversion_rate))
			
def validate_price_list(args):
	if args.get("price_list"):
		if not frappe.db.get_value("Price List", 
			{"name": args.price_list, args.transaction_type: 1, "enabled": 1}):
				throw(_("Price List is either disabled or for not ") + _(args.transaction_type))
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
	
def get_party_item_code(args, item_bean, out):
	if args.transaction_type == "selling":
		customer_item_code = item_bean.doclist.get({"parentfield": "item_customer_details",
			"customer_name": args.customer})
		out.customer_item_code = customer_item_code[0].ref_code if customer_item_code else None
	else:
		item_supplier = item_bean.doclist.get({"parentfield": "item_supplier_details",
			"supplier": args.supplier})
		out.supplier_part_no = item_supplier[0].supplier_part_no if item_supplier else None
		

def get_pos_settings_item_details(company, args, pos_settings=None):
	res = frappe._dict()
	
	if not pos_settings:
		pos_settings = get_pos_settings(company)
		
	if pos_settings:
		for fieldname in ("income_account", "cost_center", "warehouse", "expense_account"):
			if not args.get(fieldname):
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
	
def apply_pricing_rule(out, args):
	args_dict = frappe._dict().update(args)
	args_dict.update(out)
	all_pricing_rules = get_pricing_rules(args_dict)

	for rule_for in ["price", "discount_percentage"]:
		pricing_rules = filter(lambda x: x[rule_for] > 0.0, all_pricing_rules)
		pricing_rules = filter_pricing_rules(args_dict, pricing_rules, rule_for)

		if pricing_rules:
			if rule_for == "discount_percentage":
				out["discount_percentage"] = pricing_rules[-1]["discount_percentage"]
				out["pricing_rule_for_discount"] = pricing_rules[-1]["name"]
			else:
				out["base_price_list_rate"] = pricing_rules[0]["price"]
				out["price_list_rate"] = pricing_rules[0]["price"] * \
					flt(args_dict.plc_conversion_rate) / flt(args_dict.conversion_rate)
				out["pricing_rule_for_price"] = pricing_rules[-1]["name"]
	
def get_pricing_rules(args_dict):	
	conditions = ""
	for field in ["customer", "customer_group", "territory", "supplier", "supplier_type", 
		"campaign", "sales_partner"]:
			if args_dict.get(field):
				conditions += " and ifnull("+field+", '') in (%("+field+")s, '')"
			else:
				conditions += " and ifnull("+field+", '') = ''"
	
	conditions += " and ifnull(for_price_list, '') in (%(price_list)s, '')"
	
	if args_dict.get("transaction_date"):
		conditions += """ and %(transaction_date)s between ifnull(valid_from, '2000-01-01') 
			and ifnull(valid_upto, '2500-12-31')"""
	
	return frappe.db.sql("""select * from `tabPricing Rule` 
		where (item_code=%(item_code)s or item_group=%(item_group)s or brand=%(brand)s) 
			and docstatus < 2 and ifnull(disable, 0) = 0 {0}
		order by priority desc, name desc""".format(conditions), args_dict, as_dict=1)

def filter_pricing_rules(args_dict, pricing_rules, price_or_discount):
	# filter for qty
	if pricing_rules and args_dict.get("qty"):
		pricing_rules = filter(lambda x: (args_dict.qty>=flt(x.min_qty) 
			and (args_dict.qty<=x.max_qty if x.max_qty else True)), pricing_rules)
 
	# find pricing rule with highest priority
	if pricing_rules:
		max_priority = max([cint(p.priority) for p in pricing_rules])
		if max_priority:
			pricing_rules = filter(lambda x: cint(x.priority)==max_priority, pricing_rules)
			
	# apply internal priority
	all_fields = ["item_code", "item_group", "brand", "customer", "customer_group", "territory", 
		"supplier", "supplier_type", "campaign", "for_price_list", "sales_partner"]
	
	if len(pricing_rules) > 1:
		for field_set in [["item_code", "item_group", "brand"], 
			["customer", "customer_group", "territory"], ["supplier", "supplier_type"]]:
				remaining_fields = list(set(all_fields) - set(field_set))
				if if_all_rules_same(pricing_rules, remaining_fields):
					pricing_rules = apply_internal_priority(pricing_rules, field_set, args_dict)
					break

		if len(pricing_rules) > 1:
			pricing_rules = sorted(pricing_rules, key=lambda x: x[price_or_discount])
	
	return pricing_rules

def if_all_rules_same(pricing_rules, fields):
	all_rules_same = True
	val = [pricing_rules[0][k] for k in fields]
	for p in pricing_rules[1:]:
		if val != [p[k] for k in fields]:
			all_rules_same = False
			break
	
	return all_rules_same

def apply_internal_priority(pricing_rules, field_set, args_dict):
	filtered_rules = []
	for field in field_set:
		if args_dict.get(field):
			filtered_rules = filter(lambda x: x[field]==args_dict[field], pricing_rules)
			if filtered_rules: break

	return filtered_rules or pricing_rules

def get_serial_nos_by_fifo(args, item_bean):
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