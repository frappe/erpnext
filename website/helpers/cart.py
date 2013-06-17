# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
import webnotes.defaults
from webnotes.utils import today, get_fullname

@webnotes.whitelist()
def add_to_cart(item_code):
	update_qty(item_code, 1)
	
@webnotes.whitelist()
def remove_from_cart(item_code):
	update_qty(item_code, 0)

@webnotes.whitelist()
def update_qty(item_code, qty_to_set):
	party = get_lead_or_customer()
	quotation = get_shopping_cart_quotation(party)
	
	if qty_to_set == 0:
		quotation.set_doclist(quotation.doclist.get({"item_code": ["!=", item_code]}))
	else:
		quotation_items = quotation.doclist.get({"item_code": item_code})
		if not quotation_items:
			quotation.doclist.append({
				"doctype": "Quotation Item",
				"parentfield": "quotation_details",
				"item_code": item_code,
				"qty": qty_to_set
			})
		else:
			quotation_items[0].qty = qty_to_set
	
	quotation.ignore_permissions = True
	quotation.save()
	
	return quotation.doc.name
	
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
			"status": "Open" # TODO: set something better???
		})
		lead_bean.ignore_permissions = True
		lead_bean.insert()
		
		return lead_bean.doc
		
def get_shopping_cart_quotation(party):
	quotation = webnotes.conn.get_value("Quotation", 
		{party.doctype.lower(): party.name, "order_type": "Shopping Cart", "docstatus": 0})
	
	if quotation:
		qbean = webnotes.bean("Quotation", quotation)
	else:
		qbean = webnotes.bean({
			"doctype": "Quotation",
			"naming_series": "QTN-CART-",
			"quotation_to": "Customer",
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
				where use_for_website=1 and pl.name = plc.parent)""", country)
	
	if price_list_name:
		price_list_name = price_list_name[0][0]
	else:
		price_list_name = webnotes.conn.get_value("Price List", 
			{"use_for_website": 1, "valid_for_all_countries": 1})
			
	if not price_list_name:
		raise Exception, "No website Price List specified"
	
	return price_list_name


@webnotes.whitelist()
def checkout():
	party = get_lead_or_customer()
	quotation = get_shopping_cart_quotation(party)
	
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
		add_to_cart("_Test Item")
		
		quotation = get_shopping_cart_quotation(get_lead_or_customer())
		quotation_items = quotation.doclist.get({"parentfield": "quotation_details", "item_code": "_Test Item"})
		self.assertTrue(quotation_items)
		self.assertEquals(quotation_items[0].qty, 1)
		
		return quotation
		
	def test_update_qty(self):
		self.test_add_to_cart()

		update_qty("_Test Item", 5)
		
		quotation = get_shopping_cart_quotation(get_lead_or_customer())
		quotation_items = quotation.doclist.get({"parentfield": "quotation_details", "item_code": "_Test Item"})
		self.assertTrue(quotation_items)
		self.assertEquals(quotation_items[0].qty, 5)
		
		return quotation
		
	def test_remove_from_cart(self):
		quotation0 = self.test_add_to_cart()
		
		remove_from_cart("_Test Item")
		
		quotation = get_shopping_cart_quotation(get_lead_or_customer())
		self.assertEquals(quotation0.doc.name, quotation.doc.name)
		
		quotation_items = quotation.doclist.get({"parentfield": "quotation_details", "item_code": "_Test Item"})
		self.assertEquals(quotation_items, [])
		
	def test_checkout(self):
		quotation = self.test_update_qty()
		sales_order = checkout()
		self.assertEquals(sales_order.doclist.getone({"item_code": "_Test Item"}).prevdoc_docname, quotation.doc.name)
		