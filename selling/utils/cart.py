# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
import webnotes.defaults
from webnotes.utils import flt, get_fullname, fmt_money, cstr

class WebsitePriceListMissingError(webnotes.ValidationError): pass

def set_cart_count(quotation=None):
	if not quotation:
		quotation = _get_cart_quotation()
	cart_count = cstr(len(quotation.doclist.get({"parentfield": "quotation_details"})))
	webnotes._response.set_cookie("cart_count", cart_count)

@webnotes.whitelist()
def get_cart_quotation(doclist=None):
	party = get_lead_or_customer()
	
	if not doclist:
		quotation = _get_cart_quotation(party)
		doclist = quotation.doclist
		set_cart_count(quotation)
	
	return {
		"doclist": decorate_quotation_doclist(doclist),
		"addresses": [{"name": address.name, "display": address.display} 
			for address in get_address_docs(party)],
		"shipping_rules": get_applicable_shipping_rules(party)
	}
	
@webnotes.whitelist()
def place_order():
	quotation = _get_cart_quotation()
	controller = quotation.make_controller()
	for fieldname in ["customer_address", "shipping_address_name"]:
		if not quotation.doc.fields.get(fieldname):
			msgprint(_("Please select a") + " " + _(controller.meta.get_label(fieldname)), raise_exception=True)
	
	quotation.ignore_permissions = True
	quotation.submit()
	
	from selling.doctype.quotation.quotation import _make_sales_order
	sales_order = webnotes.bean(_make_sales_order(quotation.doc.name, ignore_permissions=True))
	sales_order.ignore_permissions = True
	sales_order.insert()
	sales_order.submit()
	webnotes._response.set_cookie("cart_count", "")
	
	return sales_order.doc.name

@webnotes.whitelist()
def update_cart(item_code, qty, with_doclist=0):
	quotation = _get_cart_quotation()
	
	qty = flt(qty)
	if qty == 0:
		quotation.set_doclist(quotation.doclist.get({"item_code": ["!=", item_code]}))
		if not quotation.doclist.get({"parentfield": "quotation_details"}) and \
			not quotation.doc.fields.get("__islocal"):
				quotation.__delete = True
			
	else:
		quotation_items = quotation.doclist.get({"item_code": item_code})
		if not quotation_items:
			quotation.doclist.append({
				"doctype": "Quotation Item",
				"parentfield": "quotation_details",
				"item_code": item_code,
				"qty": qty
			})
		else:
			quotation_items[0].qty = qty
	
	apply_cart_settings(quotation=quotation)

	if hasattr(quotation, "__delete"):
		webnotes.delete_doc("Quotation", quotation.doc.name, ignore_permissions=True)
		quotation = _get_cart_quotation()
	else:
		quotation.ignore_permissions = True
		quotation.save()
	
	set_cart_count(quotation)
	
	if with_doclist:
		return get_cart_quotation(quotation.doclist)
	else:
		return quotation.doc.name
		
@webnotes.whitelist()
def update_cart_address(address_fieldname, address_name):
	from utilities.transaction_base import get_address_display
	
	quotation = _get_cart_quotation()
	address_display = get_address_display(webnotes.doc("Address", address_name).fields)
	
	if address_fieldname == "shipping_address_name":
		quotation.doc.shipping_address_name = address_name
		quotation.doc.shipping_address = address_display
		
		if not quotation.doc.customer_address:
			address_fieldname == "customer_address"
	
	if address_fieldname == "customer_address":
		quotation.doc.customer_address = address_name
		quotation.doc.address_display = address_display
		
	
	apply_cart_settings(quotation=quotation)
	
	quotation.ignore_permissions = True
	quotation.save()
		
	return get_cart_quotation(quotation.doclist)

@webnotes.whitelist()
def get_addresses():
	return [d.fields for d in get_address_docs()]
	
@webnotes.whitelist()
def save_address(fields, address_fieldname=None):
	party = get_lead_or_customer()
	fields = webnotes.load_json(fields)
	
	if fields.get("name"):
		bean = webnotes.bean("Address", fields.get("name"))
	else:
		bean = webnotes.bean({"doctype": "Address", "__islocal": 1})
	
	bean.doc.fields.update(fields)
	
	party_fieldname = party.doctype.lower()
	bean.doc.fields.update({
		party_fieldname: party.name,
		(party_fieldname + "_name"): party.fields[party_fieldname + "_name"]
	})
	bean.ignore_permissions = True
	bean.save()
	
	if address_fieldname:
		update_cart_address(address_fieldname, bean.doc.name)
	
	return bean.doc.name
	
def get_address_docs(party=None):
	from webnotes.model.doclist import objectify
	from utilities.transaction_base import get_address_display
	
	if not party:
		party = get_lead_or_customer()
		
	address_docs = objectify(webnotes.conn.sql("""select * from `tabAddress`
		where `%s`=%s order by name""" % (party.doctype.lower(), "%s"), party.name, 
		as_dict=True, update={"doctype": "Address"}))
	
	for address in address_docs:
		address.display = get_address_display(address.fields)
		address.display = (address.display).replace("\n", "<br>\n")
		
	return address_docs
	
def get_lead_or_customer():
	customer = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user}, "customer")
	if customer:
		return webnotes.doc("Customer", customer)
	
	lead = webnotes.conn.get_value("Lead", {"email_id": webnotes.session.user})
	if lead:
		return webnotes.doc("Lead", lead)
	else:
		lead_bean = webnotes.bean({
			"doctype": "Lead",
			"email_id": webnotes.session.user,
			"lead_name": get_fullname(webnotes.session.user),
			"territory": guess_territory(),
			"status": "Open" # TODO: set something better???
		})
		
		if webnotes.session.user != "Guest":
			lead_bean.ignore_permissions = True
			lead_bean.insert()
			
		return lead_bean.doc
		
def guess_territory():
	territory = None
	geoip_country = webnotes.session.get("session_country")
	if geoip_country:
		territory = webnotes.conn.get_value("Territory", geoip_country)
	
	return territory or \
		webnotes.conn.get_value("Shopping Cart Settings", None, "territory") or \
		"All Territories"

def decorate_quotation_doclist(doclist):
	for d in doclist:
		if d.item_code:
			d.fields.update(webnotes.conn.get_value("Item", d.item_code, 
				["website_image", "description", "page_name"], as_dict=True))
			d.formatted_rate = fmt_money(d.export_rate, currency=doclist[0].currency)
			d.formatted_amount = fmt_money(d.export_amount, currency=doclist[0].currency)
		elif d.charge_type:
			d.formatted_tax_amount = fmt_money(d.tax_amount / doclist[0].conversion_rate,
				currency=doclist[0].currency)

	doclist[0].formatted_grand_total_export = fmt_money(doclist[0].grand_total_export,
		currency=doclist[0].currency)
	
	return [d.fields for d in doclist]

def _get_cart_quotation(party=None):
	if not party:
		party = get_lead_or_customer()
		
	quotation = webnotes.conn.get_value("Quotation", 
		{party.doctype.lower(): party.name, "order_type": "Shopping Cart", "docstatus": 0})
	
	if quotation:
		qbean = webnotes.bean("Quotation", quotation)
	else:
		qbean = webnotes.bean({
			"doctype": "Quotation",
			"naming_series": webnotes.defaults.get_user_default("shopping_cart_quotation_series") or "QTN-CART-",
			"quotation_to": party.doctype,
			"company": webnotes.defaults.get_user_default("company"),
			"order_type": "Shopping Cart",
			"status": "Draft",
			"docstatus": 0,
			"__islocal": 1,
			(party.doctype.lower()): party.name
		})
		
		if party.doctype == "Customer":
			qbean.doc.contact_person = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user,
				"customer": party.name})
			qbean.run_method("set_contact_fields")
		
		qbean.run_method("onload_post_render")
		apply_cart_settings(party, qbean)
	
	return qbean

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
		
		contact_name = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user,
			"customer": party.name})
		contact = webnotes.bean("Contact", contact_name)
		contact.doc.first_name = fullname
		contact.doc.last_name = None
		contact.doc.customer_name = party.customer_name
		contact.doc.mobile_no = mobile_no
		contact.doc.phone = phone
		contact.ignore_permissions = True
		contact.save()
	
	party_bean = webnotes.bean(party.fields)
	party_bean.ignore_permissions = True
	party_bean.save()
	
	qbean = _get_cart_quotation(party)
	if not qbean.doc.fields.get("__islocal"):
		qbean.doc.customer_name = company_name or fullname
		qbean.run_method("set_contact_fields")
		qbean.ignore_permissions = True
		qbean.save()

def apply_cart_settings(party=None, quotation=None):
	if not party:
		party = get_lead_or_customer()
	if not quotation:
		quotation = _get_cart_quotation(party)

	cart_settings = webnotes.get_obj("Shopping Cart Settings")
	
	billing_territory = get_address_territory(quotation.doc.customer_address) or \
		party.territory or "All Territories"
		
	set_price_list_and_rate(quotation, cart_settings, billing_territory)
	
	quotation.run_method("calculate_taxes_and_totals")
	
	set_taxes(quotation, cart_settings, billing_territory)
	
	_apply_shipping_rule(party, quotation, cart_settings)
	
def set_price_list_and_rate(quotation, cart_settings, billing_territory):
	"""set price list based on billing territory"""
	quotation.doc.selling_price_list = cart_settings.get_price_list(billing_territory)
	
	# reset values
	quotation.doc.price_list_currency = quotation.doc.currency = \
		quotation.doc.plc_conversion_rate = quotation.doc.conversion_rate = None
	for item in quotation.doclist.get({"parentfield": "quotation_details"}):
		item.ref_rate = item.adj_rate = item.export_rate = item.export_amount = None
	
	# refetch values
	quotation.run_method("set_price_list_and_item_details")
	
	# set it in cookies for using in product page
	if quotation.doc.selling_price_list:
		webnotes.local._response.set_cookie("selling_price_list", quotation.doc.selling_price_list)
	
def set_taxes(quotation, cart_settings, billing_territory):
	"""set taxes based on billing territory"""
	quotation.doc.charge = cart_settings.get_tax_master(billing_territory)

	# clear table
	quotation.set_doclist(quotation.doclist.get({"parentfield": ["!=", "other_charges"]}))
	
	# append taxes
	controller = quotation.make_controller()
	controller.append_taxes_from_master("other_charges", "charge")
	quotation.set_doclist(controller.doclist)

@webnotes.whitelist()
def apply_shipping_rule(shipping_rule):
	quotation = _get_cart_quotation()
	
	quotation.doc.shipping_rule = shipping_rule
	
	apply_cart_settings(quotation=quotation)
	
	quotation.ignore_permissions = True
	quotation.save()
	
	return get_cart_quotation(quotation.doclist)
	
def _apply_shipping_rule(party=None, quotation=None, cart_settings=None):
	shipping_rules = get_shipping_rules(party, quotation, cart_settings)
	
	if not shipping_rules:
		return
		
	elif quotation.doc.shipping_rule not in shipping_rules:
		quotation.doc.shipping_rule = shipping_rules[0]
	
	quotation.run_method("apply_shipping_rule")
	quotation.run_method("calculate_taxes_and_totals")
	
def get_applicable_shipping_rules(party=None, quotation=None):
	shipping_rules = get_shipping_rules(party, quotation)
	
	if shipping_rules:
		rule_label_map = webnotes.conn.get_values("Shipping Rule", shipping_rules, "label")
		# we need this in sorted order as per the position of the rule in the settings page
		return [[rule, rule_label_map.get(rule)] for rule in shipping_rules]
		
def get_shipping_rules(party=None, quotation=None, cart_settings=None):
	if not party:
		party = get_lead_or_customer()
	if not quotation:
		quotation = _get_cart_quotation()
	if not cart_settings:
		cart_settings = webnotes.get_obj("Shopping Cart Settings")
		
	# set shipping rule based on shipping territory	
	shipping_territory = get_address_territory(quotation.doc.shipping_address_name) or \
		party.territory
	
	shipping_rules = cart_settings.get_shipping_rules(shipping_territory)
	
	return shipping_rules
	
def get_address_territory(address_name):
	"""Tries to match city, state and country of address to existing territory"""
	territory = None

	if address_name:
		address_fields = webnotes.conn.get_value("Address", address_name, 
			["city", "state", "country"])
		for value in address_fields:
			territory = webnotes.conn.get_value("Territory", value)
			if territory:
				break
	
	return territory
	
import unittest
test_dependencies = ["Item", "Price List", "Contact", "Shopping Cart Settings"]

class TestCart(unittest.TestCase):
	def tearDown(self):
		return
		
		cart_settings = webnotes.bean("Shopping Cart Settings")
		cart_settings.ignore_permissions = True
		cart_settings.doc.enabled = 0
		cart_settings.save()
	
	def enable_shopping_cart(self):
		return
		if not webnotes.conn.get_value("Shopping Cart Settings", None, "enabled"):
			cart_settings = webnotes.bean("Shopping Cart Settings")
			cart_settings.ignore_permissions = True
			cart_settings.doc.enabled = 1
			cart_settings.save()
			
	def test_get_lead_or_customer(self):
		webnotes.session.user = "test@example.com"
		party1 = get_lead_or_customer()
		party2 = get_lead_or_customer()
		self.assertEquals(party1.name, party2.name)
		self.assertEquals(party1.doctype, "Lead")
		
		webnotes.session.user = "test_contact_customer@example.com"
		party = get_lead_or_customer()
		self.assertEquals(party.name, "_Test Customer")
		
	def test_add_to_cart(self):
		self.enable_shopping_cart()
		webnotes.session.user = "test@example.com"
		
		update_cart("_Test Item", 1)
		
		quotation = _get_cart_quotation()
		quotation_items = quotation.doclist.get({"parentfield": "quotation_details", "item_code": "_Test Item"})
		self.assertTrue(quotation_items)
		self.assertEquals(quotation_items[0].qty, 1)
		
		return quotation
		
	def test_update_cart(self):
		self.test_add_to_cart()

		update_cart("_Test Item", 5)
		
		quotation = _get_cart_quotation()
		quotation_items = quotation.doclist.get({"parentfield": "quotation_details", "item_code": "_Test Item"})
		self.assertTrue(quotation_items)
		self.assertEquals(quotation_items[0].qty, 5)
		
		return quotation
		
	def test_remove_from_cart(self):
		quotation0 = self.test_add_to_cart()
		
		update_cart("_Test Item", 0)
		
		quotation = _get_cart_quotation()
		self.assertEquals(quotation0.doc.name, quotation.doc.name)
		
		quotation_items = quotation.doclist.get({"parentfield": "quotation_details", "item_code": "_Test Item"})
		self.assertEquals(quotation_items, [])
		
	def test_place_order(self):
		quotation = self.test_update_cart()
		sales_order_name = place_order()
		sales_order = webnotes.bean("Sales Order", sales_order_name)
		self.assertEquals(sales_order.doclist.getone({"item_code": "_Test Item"}).prevdoc_docname, quotation.doc.name)
		