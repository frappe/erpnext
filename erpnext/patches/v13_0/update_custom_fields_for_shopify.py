# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.erpnext_integrations.doctype.shopify_settings.shopify_settings import setup_custom_fields

def execute():
	if frappe.db.get_single_value('Shopify Settings', 'enable_shopify'):
		setup_custom_fields()
