# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import dateutil
from amazon_methods import get_products_details, get_orders

class AmazonMWSSettings(Document):
	def get_products_details(self):
		products = get_products_details()

	def get_order_details(self):
		after_date = dateutil.parser.parse(self.after_date).strftime("%Y-%m-%d")
		orders = get_orders(after_date = after_date)

def schedule_get_order_details():
	mws_settings = frappe.get_doc("Amazon MWS Settings")
	if mws_settings.enable_synch:
		after_date = dateutil.parser.parse(mws_settings.after_date).strftime("%Y-%m-%d")
		orders = get_orders(after_date = after_date)