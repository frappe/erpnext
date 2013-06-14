# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
import webnotes.defaults
from webnotes.utils import today, get_fullname
import json

@webnotes.whitelist()
def checkout(cart):
	# webnotes.msgprint(cart);
	if isinstance(cart, basestring):
		cart = json.loads(cart) or {}
	
	if webnotes.session.user == "Guest":
		msgprint(_("Please login before you checkout!"), raise_exception=True)
	elif webnotes.conn.get_value("Profile", webnotes.session.user, "user_type") != "Partner":
		msgprint(_("Illegal User"), raise_exception=True)
	
	# make_quotation(cart)

def make_quotation(cart):
	from accounts.utils import get_fiscal_year
	
	quotation_defaults = webnotes._dict({
		"doctype": "Quotation",
		"naming_series": "QTN-13-14-",
		"quotation_to": "Customer",
		"company": webnotes.defaults.get_user_default("company"),
		"order_type": "Sales",
		"status": "Draft",
	})
	
	quotation = webnotes.bean(quotation_defaults)
	quotation.doc.fields.update({
		"transaction_date": today(),
		"fiscal_year": get_fiscal_year(today()),
		
		# TODO
		"price_list_name": "fetch",
		"price_list_currency": "fetch",
		"plc_conversion_rate": "something",
		"currency": "same as price_list_currency",
		"conversion_rate": "same as plc_converion_rate",
		"territory": "fetch",
		
		
	})
	
	# TODO add items
	for item_code, item in cart.items():
		pass
		
	# TODO apply taxes
	
	# save and submit

@webnotes.whitelist()
def add_to_cart(item_code):
	party = get_lead_or_customer()
	quotation = get_shopping_cart_quotation(party)
	
	quotation_items = quotation.doclist.get({"parentfield": "quotation_details", "item_code": item_code})
	if not quotation_items:
		quotation.doclist.append({
			"doctype": "Quotation Item",
			"parentfield": "quotation_details",
			"item_code": item_code,
			"qty": 1
		})
	
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

@webnotes.whitelist()
def remove_from_cart(item_code):
	pass
	
@webnotes.whitelist()
def update_qty(item_code, qty):
	pass
	
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

import unittest

test_dependencies = ["Item", "Price List"]

class TestCart(unittest.TestCase):
	def test_add_to_cart(self):
		webnotes.session.user = "test@example.com"
		add_to_cart("_Test Item")
		
	def test_change_qty(self):
		pass
		
	def test_remove_from_cart(self):
		pass
		
	def test_checkout(self):
		pass
		