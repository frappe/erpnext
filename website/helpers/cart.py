# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals
import webnotes
import webnotes.defaults
from webnotes.utils import cint, get_fullname, fmt_money

class WebsitePriceListMissingError(webnotes.ValidationError): pass

@webnotes.whitelist()
def get_cart_quotation(doclist=None):
	party = get_lead_or_customer()
	
	if not doclist:
		doclist = _get_cart_quotation(party).doclist
	
	return {
		"doclist": decorate_quotation_doclist(doclist),
		"addresses": [{"name": address.name, "display": address.display} 
			for address in get_address_docs(party)]
	}

@webnotes.whitelist()
def update_cart(item_code, qty, with_doclist=0):
	quotation = _get_cart_quotation()
	
	qty = cint(qty)
	if qty == 0:
		quotation.set_doclist(quotation.doclist.get({"item_code": ["!=", item_code]}))
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
	
	quotation.ignore_permissions = True
	quotation.save()
	
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
			"territory": webnotes.conn.get_value("Shopping Cart Settings", None, "territory") or \
				"All Territories",
			"status": "Open" # TODO: set something better???
		})
		lead_bean.ignore_permissions = True
		lead_bean.insert()
		
		return lead_bean.doc

def decorate_quotation_doclist(doclist):
	for d in doclist:
		if d.item_code:
			d.fields.update(webnotes.conn.get_value("Item", d.item_code, 
				["website_image", "web_short_description", "page_name"], as_dict=True))
			d.formatted_rate = fmt_money(d.export_rate, currency=doclist[0].currency)
			d.formatted_amount = fmt_money(d.export_amount, currency=doclist[0].currency)

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
			"naming_series": "QTN-CART-",
			"quotation_to": party.doctype,
			"company": webnotes.defaults.get_user_default("company"),
			"order_type": "Shopping Cart",
			"status": "Draft",
			"__islocal": 1,
			"price_list_name": get_price_list(party),
			(party.doctype.lower()): party.name
		})
	
	return qbean
	
def get_price_list(party):
	if not party.default_price_list:
		party.default_price_list = get_price_list_using_geoip()
		party.save()
		
	return party.default_price_list

def get_price_list_using_geoip():
	country = webnotes.session.get("session_country")
	price_list_name = None

	if country:
		price_list_name = webnotes.conn.sql("""select parent 
			from `tabPrice List Country` plc
			where country=%s and exists (select name from `tabPrice List` pl
				where use_for_website=1 and ifnull(valid_for_all_countries, 0)=0 and 
				pl.name = plc.parent)""", country)
	
	if price_list_name:
		price_list_name = price_list_name[0][0]
	else:
		price_list_name = webnotes.conn.get_value("Price List", 
			{"use_for_website": 1, "valid_for_all_countries": 1})
			
	if not price_list_name:
		raise WebsitePriceListMissingError, "No website Price List specified"
	
	return price_list_name


@webnotes.whitelist()
def checkout():
	quotation = _get_cart_quotation()
	
	quotation.ignore_permissions = True
	quotation.submit()
	
	sales_order = webnotes.bean(webnotes.map_doclist([["Quotation", "Sales Order"], ["Quotation Item", "Sales Order Item"],
		["Sales Taxes and Charges", "Sales Taxes and Charges"]], quotation.doc.name))
		
	sales_order.ignore_permissions = True
	sales_order.insert()
	sales_order.submit()
	
	return sales_order

import unittest
test_dependencies = ["Item", "Price List", "Contact"]

class TestCart(unittest.TestCase):
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
		
	def test_checkout(self):
		quotation = self.test_update_cart()
		sales_order = checkout()
		self.assertEquals(sales_order.doclist.getone({"item_code": "_Test Item"}).prevdoc_docname, quotation.doc.name)
		