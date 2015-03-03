# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import frappe.defaults
from frappe.utils import flt, get_fullname, fmt_money, cstr
from erpnext.utilities.doctype.address.address import get_address_display
from frappe.utils.nestedset import get_root_of

class WebsitePriceListMissingError(frappe.ValidationError): pass

def set_cart_count(quotation=None):
	if not quotation:
		quotation = _get_cart_quotation()
	cart_count = cstr(len(quotation.get("items")))
	frappe.local.cookie_manager.set_cookie("cart_count", cart_count)

@frappe.whitelist()
def get_cart_quotation(doc=None):
	party = get_lead_or_customer()

	if not doc:
		quotation = _get_cart_quotation(party)
		doc = quotation
		set_cart_count(quotation)

	return {
		"doc": decorate_quotation_doc(doc),
		"addresses": [{"name": address.name, "display": address.display}
			for address in get_address_docs(party)],
		"shipping_rules": get_applicable_shipping_rules(party)
	}

@frappe.whitelist()
def place_order():
	quotation = _get_cart_quotation()
	quotation.company = frappe.db.get_value("Shopping Cart Settings", None, "company")
	for fieldname in ["customer_address", "shipping_address_name"]:
		if not quotation.get(fieldname):
			throw(_("{0} is required").format(quotation.meta.get_label(fieldname)))

	quotation.flags.ignore_permissions = True
	quotation.submit()

	if quotation.lead:
		# company used to create customer accounts
		frappe.defaults.set_user_default("company", quotation.company)

	from erpnext.selling.doctype.quotation.quotation import _make_sales_order
	sales_order = frappe.get_doc(_make_sales_order(quotation.name, ignore_permissions=True))
	for item in sales_order.get("items"):
		item.reserved_warehouse = frappe.db.get_value("Item", item.item_code, "website_warehouse") or None

	sales_order.flags.ignore_permissions = True
	sales_order.insert()
	sales_order.submit()
	frappe.local.cookie_manager.delete_cookie("cart_count")

	return sales_order.name

@frappe.whitelist()
def update_cart(item_code, qty, with_doc):
	quotation = _get_cart_quotation()

	qty = flt(qty)
	if qty == 0:
		quotation.set("items", quotation.get("items", {"item_code": ["!=", item_code]}))
		if not quotation.get("items") and \
			not quotation.get("__islocal"):
				quotation.__delete = True

	else:
		quotation_items = quotation.get("items", {"item_code": item_code})
		if not quotation_items:
			quotation.append("items", {
				"doctype": "Quotation Item",
				"item_code": item_code,
				"qty": qty
			})
		else:
			quotation_items[0].qty = qty

	apply_cart_settings(quotation=quotation)

	if hasattr(quotation, "__delete"):
		frappe.delete_doc("Quotation", quotation.name, ignore_permissions=True)
		quotation = _get_cart_quotation()
	else:
		quotation.flags.ignore_permissions = True
		quotation.save()

	set_cart_count(quotation)

	if with_doc:
		return get_cart_quotation(quotation)
	else:
		return quotation.name

@frappe.whitelist()
def update_cart_address(address_fieldname, address_name):
	quotation = _get_cart_quotation()
	address_display = get_address_display(frappe.get_doc("Address", address_name).as_dict())

	if address_fieldname == "shipping_address_name":
		quotation.shipping_address_name = address_name
		quotation.shipping_address = address_display

		if not quotation.customer_address:
			address_fieldname == "customer_address"

	if address_fieldname == "customer_address":
		quotation.customer_address = address_name
		quotation.address_display = address_display


	apply_cart_settings(quotation=quotation)

	quotation.flags.ignore_permissions = True
	quotation.save()

	return get_cart_quotation(quotation)

def guess_territory():
	territory = None
	geoip_country = frappe.session.get("session_country")
	if geoip_country:
		territory = frappe.db.get_value("Territory", geoip_country)

	return territory or \
		frappe.db.get_value("Shopping Cart Settings", None, "territory") or \
			get_root_of("Territory")

def decorate_quotation_doc(quotation_doc):
	doc = frappe._dict(quotation_doc.as_dict())
	for d in doc.get("items", []):
		d.update(frappe.db.get_value("Item", d["item_code"],
			["website_image", "description", "page_name"], as_dict=True))
		d["formatted_rate"] = fmt_money(d.get("rate"), currency=doc.currency)
		d["formatted_amount"] = fmt_money(d.get("amount"), currency=doc.currency)

	for d in doc.get("taxes", []):
		d["formatted_tax_amount"] = fmt_money(flt(d.get("tax_amount_after_discount_amount")),
			currency=doc.currency)

	doc.formatted_grand_total_export = fmt_money(doc.grand_total,
		currency=doc.currency)

	return doc

def _get_cart_quotation(party=None):
	if not party:
		party = get_lead_or_customer()

	quotation = frappe.db.get_value("Quotation",
		{party.doctype.lower(): party.name, "order_type": "Shopping Cart", "docstatus": 0})

	if quotation:
		qdoc = frappe.get_doc("Quotation", quotation)
	else:
		qdoc = frappe.get_doc({
			"doctype": "Quotation",
			"naming_series": frappe.defaults.get_user_default("shopping_cart_quotation_series") or "QTN-CART-",
			"quotation_to": party.doctype,
			"company": frappe.db.get_value("Shopping Cart Settings", None, "company"),
			"order_type": "Shopping Cart",
			"status": "Draft",
			"docstatus": 0,
			"__islocal": 1,
			(party.doctype.lower()): party.name
		})

		if party.doctype == "Customer":
			qdoc.contact_person = frappe.db.get_value("Contact", {"email_id": frappe.session.user,
				"customer": party.name})

		qdoc.flags.ignore_permissions = True
		qdoc.run_method("set_missing_values")
		apply_cart_settings(party, qdoc)

	return qdoc

def update_party(fullname, company_name=None, mobile_no=None, phone=None):
	party = get_lead_or_customer()

	if party.doctype == "Lead":
		party.company_name = company_name
		party.lead_name = fullname
		party.mobile_no = mobile_no
		party.phone = phone
	else:
		party.customer_name = company_name or fullname
		party.customer_type == "Company" if company_name else "Individual"

		contact_name = frappe.db.get_value("Contact", {"email_id": frappe.session.user,
			"customer": party.name})
		contact = frappe.get_doc("Contact", contact_name)
		contact.first_name = fullname
		contact.last_name = None
		contact.customer_name = party.customer_name
		contact.mobile_no = mobile_no
		contact.phone = phone
		contact.flags.ignore_permissions = True
		contact.save()

	party_doc = frappe.get_doc(party.as_dict())
	party_doc.flags.ignore_permissions = True
	party_doc.save()

	qdoc = _get_cart_quotation(party)
	if not qdoc.get("__islocal"):
		qdoc.customer_name = company_name or fullname
		qdoc.run_method("set_missing_lead_customer_details")
		qdoc.flags.ignore_permissions = True
		qdoc.save()

def apply_cart_settings(party=None, quotation=None):
	if not party:
		party = get_lead_or_customer()
	if not quotation:
		quotation = _get_cart_quotation(party)

	cart_settings = frappe.get_doc("Shopping Cart Settings")
	billing_territory = get_address_territory(quotation.customer_address) or \
		party.territory or get_root_of("Territory")

	set_price_list_and_rate(quotation, cart_settings, billing_territory)

	quotation.run_method("calculate_taxes_and_totals")

	set_taxes(quotation, cart_settings, billing_territory)

	_apply_shipping_rule(party, quotation, cart_settings)

def set_price_list_and_rate(quotation, cart_settings, billing_territory):
	"""set price list based on billing territory"""
	quotation.selling_price_list = cart_settings.get_price_list(billing_territory)
	# reset values
	quotation.price_list_currency = quotation.currency = \
		quotation.plc_conversion_rate = quotation.conversion_rate = None
	for item in quotation.get("items"):
		item.price_list_rate = item.discount_percentage = item.rate = item.amount = None

	# refetch values
	quotation.run_method("set_price_list_and_item_details")

	# set it in cookies for using in product page
	frappe.local.cookie_manager.set_cookie("selling_price_list", quotation.selling_price_list)

def set_taxes(quotation, cart_settings, billing_territory):
	"""set taxes based on billing territory"""
	quotation.taxes_and_charges = cart_settings.get_tax_master(billing_territory)

	# clear table
	quotation.set("taxes", [])

	# append taxes
	quotation.append_taxes_from_master("taxes", "taxes_and_charges")

def get_lead_or_customer():
	customer = frappe.db.get_value("Contact", {"email_id": frappe.session.user}, "customer")
	if customer:
		return frappe.get_doc("Customer", customer)

	lead = frappe.db.get_value("Lead", {"email_id": frappe.session.user})
	if lead:
		return frappe.get_doc("Lead", lead)
	else:
		lead_doc = frappe.get_doc({
			"doctype": "Lead",
			"email_id": frappe.session.user,
			"lead_name": get_fullname(frappe.session.user),
			"territory": guess_territory(),
			"status": "Open" # TODO: set something better???
		})

		if frappe.session.user not in ("Guest", "Administrator"):
			lead_doc.flags.ignore_permissions = True
			lead_doc.insert()

		return lead_doc

def get_address_docs(party=None):
	if not party:
		party = get_lead_or_customer()

	address_docs = frappe.db.sql("""select * from `tabAddress`
		where `%s`=%s order by name""" % (party.doctype.lower(), "%s"), party.name,
		as_dict=True, update={"doctype": "Address"})

	for address in address_docs:
		address.display = get_address_display(address)
		address.display = (address.display).replace("\n", "<br>\n")

	return address_docs

@frappe.whitelist()
def apply_shipping_rule(shipping_rule):
	quotation = _get_cart_quotation()

	quotation.shipping_rule = shipping_rule

	apply_cart_settings(quotation=quotation)

	quotation.flags.ignore_permissions = True
	quotation.save()

	return get_cart_quotation(quotation)

def _apply_shipping_rule(party=None, quotation=None, cart_settings=None):
	shipping_rules = get_shipping_rules(party, quotation, cart_settings)

	if not shipping_rules:
		return

	elif quotation.shipping_rule not in shipping_rules:
		quotation.shipping_rule = shipping_rules[0]

	quotation.run_method("apply_shipping_rule")
	quotation.run_method("calculate_taxes_and_totals")

def get_applicable_shipping_rules(party=None, quotation=None):
	shipping_rules = get_shipping_rules(party, quotation)

	if shipping_rules:
		rule_label_map = frappe.db.get_values("Shipping Rule", shipping_rules, "label")
		# we need this in sorted order as per the position of the rule in the settings page
		return [[rule, rule_label_map.get(rule)] for rule in shipping_rules]

def get_shipping_rules(party=None, quotation=None, cart_settings=None):
	if not party:
		party = get_lead_or_customer()
	if not quotation:
		quotation = _get_cart_quotation()
	if not cart_settings:
		cart_settings = frappe.get_doc("Shopping Cart Settings")

	# set shipping rule based on shipping territory
	shipping_territory = get_address_territory(quotation.shipping_address_name) or \
		party.territory

	shipping_rules = cart_settings.get_shipping_rules(shipping_territory)

	return shipping_rules

def get_address_territory(address_name):
	"""Tries to match city, state and country of address to existing territory"""
	territory = None

	if address_name:
		address_fields = frappe.db.get_value("Address", address_name,
			["city", "state", "country"])
		for value in address_fields:
			territory = frappe.db.get_value("Territory", value)
			if territory:
				break

	return territory
