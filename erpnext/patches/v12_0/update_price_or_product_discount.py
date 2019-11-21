from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql(""" UPDATE `tabPricing Rule` SET price_or_product_discount = 'Price'
		WHERE ifnull(price_or_product_discount,'') = '' """)