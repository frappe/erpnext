# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext import get_company_currency
from erpnext.accounts.party import get_default_price_list as get_party_default_price_list
from erpnext.controllers.accounts_controller import validate_conversion_rate
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.get_item_details import get_price_list_rate_for

_ORDER_TYPE_CONFIG = {
	"Selling": {
		"exchange_rate_type": "for_selling",
		"opposite_price_list_field": "buying_price_list",
		"party_field": "customer",
		"party_type": "Customer",
		"price_list_field": "selling_price_list",
		"price_list_type": "Selling",
		"settings_doctype": "Selling Settings",
	},
	"Purchasing": {
		"exchange_rate_type": "for_buying",
		"opposite_price_list_field": "selling_price_list",
		"party_field": "supplier",
		"party_type": "Supplier",
		"price_list_field": "buying_price_list",
		"price_list_type": "Buying",
		"settings_doctype": "Buying Settings",
	},
}


def get_order_type_config(blanket_order_type):
	return _ORDER_TYPE_CONFIG[blanket_order_type]


def get_exchange_rate_to_company(doc, currency):
	config = get_order_type_config(doc.blanket_order_type)
	return get_exchange_rate(
		currency,
		get_company_currency(doc.company),
		doc.from_date,
		config["exchange_rate_type"],
	)


def set_price_list(doc, set_default=False, force_exchange_rate=False):
	config = get_order_type_config(doc.blanket_order_type)
	fieldname = config["price_list_field"]
	doc.set(config["opposite_price_list_field"], None)

	if not doc.get(fieldname) and (doc.is_new() or set_default):
		doc.set(fieldname, get_default_price_list(doc))

	price_list = doc.get(fieldname)
	if not price_list:
		clear_price_list(doc)
		return

	price_list_type = config["price_list_type"].lower()
	price_list_details = frappe.get_cached_value(
		"Price List", price_list, ["currency", price_list_type, "enabled"], as_dict=True
	)
	if not price_list_details or not price_list_details.enabled:
		frappe.throw(_("Price List {0} is disabled or does not exist").format(frappe.bold(price_list)))
	if not price_list_details.get(price_list_type):
		frappe.throw(
			_("Price List {0} is not enabled for {1}").format(
				frappe.bold(price_list), frappe.bold(doc.blanket_order_type)
			)
		)

	price_list_currency_changed = doc.price_list_currency != price_list_details.currency
	doc.price_list_currency = price_list_details.currency
	company_currency = get_company_currency(doc.company)
	if doc.price_list_currency == company_currency:
		doc.plc_conversion_rate = 1.0
	elif price_list_currency_changed or not doc.plc_conversion_rate or force_exchange_rate:
		doc.plc_conversion_rate = get_exchange_rate_to_company(doc, doc.price_list_currency)

	validate_conversion_rate(
		doc.price_list_currency,
		doc.plc_conversion_rate,
		doc.meta.get_translated_label("plc_conversion_rate"),
		doc.company,
	)
	doc.plc_conversion_rate = flt(doc.plc_conversion_rate, doc.precision("plc_conversion_rate"))


def clear_price_list(doc):
	doc.price_list_currency = None
	doc.plc_conversion_rate = 0
	for item in doc.items:
		item.price_list_rate = 0
		item.base_price_list_rate = 0


def get_default_price_list(doc):
	config = get_order_type_config(doc.blanket_order_type)
	party_type = config["party_type"]
	party = doc.get(config["party_field"])
	if party:
		party_price_list = get_party_default_price_list(frappe.get_cached_doc(party_type, party))
		if party_price_list:
			return party_price_list

	return frappe.db.get_single_value(config["settings_doctype"], config["price_list_field"])


def get_price_list_rates(doc, item_name=None):
	price_list = doc.get(get_order_type_config(doc.blanket_order_type)["price_list_field"])
	items = [item for item in doc.items if item.item_code and (not item_name or item.name == item_name)]
	if not items:
		return []
	if not price_list:
		return [{"name": item.name, "price_list_rate": 0, "base_price_list_rate": 0} for item in items]

	stock_uoms = dict(
		frappe.get_all(
			"Item",
			filters={"name": ("in", [item.item_code for item in items])},
			fields=["name", "stock_uom"],
			as_list=True,
		)
	)

	ctx = frappe._dict(
		{
			"price_list": price_list,
			"customer": doc.customer,
			"supplier": doc.supplier,
			"transaction_date": doc.from_date,
		}
	)
	rates = []
	for item in items:
		stock_uom = stock_uoms.get(item.item_code)
		ctx.update(
			{
				"qty": flt(item.qty) or 1,
				"uom": stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1,
			}
		)
		price_list_rate = get_price_list_rate_for(ctx, item.item_code)
		rate_details = {"name": item.name, "price_list_rate": 0, "base_price_list_rate": 0}
		if price_list_rate is not None:
			rate = flt(price_list_rate) * flt(doc.plc_conversion_rate) / flt(doc.conversion_rate)
			price_list_rate, base_price_list_rate = get_rate_and_base_amount(
				doc, item, "price_list_rate", rate
			)
			rate, base_rate = get_rate_and_base_amount(doc, item, "rate", rate)
			rate_details.update(
				{
					"price_list_rate": price_list_rate,
					"base_price_list_rate": base_price_list_rate,
					"rate": rate,
					"base_rate": base_rate,
				}
			)
		rates.append(rate_details)

	return rates


def set_base_rates(doc):
	for item in doc.items:
		for fieldname in ("price_list_rate", "rate"):
			rate, base_rate = get_rate_and_base_amount(doc, item, fieldname, item.get(fieldname))
			item.set(fieldname, rate)
			item.set(f"base_{fieldname}", base_rate)


def get_rate_and_base_amount(doc, item, fieldname, rate):
	rate = flt(rate, item.precision(fieldname))
	base_fieldname = f"base_{fieldname}"
	base_rate = flt(rate * flt(doc.conversion_rate), item.precision(base_fieldname))
	return rate, base_rate


def apply_price_list(
	doc,
	item_name=None,
	reset_party_values=False,
	reset_plc_conversion_rate=False,
	reset_conversion_rate=False,
):
	doc = frappe.get_doc(frappe.parse_json(doc))
	reset_party_values = cint(reset_party_values)
	reset_plc_conversion_rate = cint(reset_plc_conversion_rate)
	reset_conversion_rate = cint(reset_conversion_rate)
	if reset_party_values:
		doc.currency = None
		doc.conversion_rate = 0
		doc.selling_price_list = None
		doc.buying_price_list = None
		doc.price_list_currency = None
		doc.plc_conversion_rate = 0
	else:
		if reset_conversion_rate:
			doc.conversion_rate = 0
		if reset_plc_conversion_rate:
			doc.plc_conversion_rate = 0

	doc.set_currency()
	doc.set_conversion_rate()
	set_price_list(
		doc,
		set_default=reset_party_values,
		force_exchange_rate=reset_party_values or reset_plc_conversion_rate,
	)

	return {
		"parent": {
			"currency": doc.currency,
			"conversion_rate": doc.conversion_rate,
			"selling_price_list": doc.selling_price_list,
			"buying_price_list": doc.buying_price_list,
			"price_list_currency": doc.price_list_currency,
			"plc_conversion_rate": doc.plc_conversion_rate,
		},
		"children": get_price_list_rates(doc, item_name),
	}
