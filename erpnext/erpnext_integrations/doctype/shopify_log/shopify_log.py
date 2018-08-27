# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from erpnext.erpnext_integrations.utils import get_webhook_address

class ShopifyLog(Document):
	pass


def make_shopify_log(status="Queued", message=None, exception=False):
	# if name not provided by log calling method then fetch existing queued state log
	if not frappe.flags.request_id:
		return

	log = frappe.get_doc("Shopify Log", frappe.flags.request_id)

	if exception:
		frappe.db.rollback()
		log = frappe.get_doc({"doctype":"Shopify Log"}).insert(ignore_permissions=True)

	log.message = message if message else ''
	log.traceback = frappe.get_traceback()
	log.status = status
	log.save(ignore_permissions=True)
	frappe.db.commit()

def dump_request_data(data, event="create/order"):
	event_mapper = {
		"orders/create": get_webhook_address(connector_name='shopify_connection', method="sync_sales_order", exclude_uri=True),
		"orders/paid" : get_webhook_address(connector_name='shopify_connection', method="prepare_sales_invoice", exclude_uri=True),
		"orders/fulfilled": get_webhook_address(connector_name='shopify_connection', method="prepare_delivery_note", exclude_uri=True)
	}

	log = frappe.get_doc({
		"doctype": "Shopify Log",
		"request_data": json.dumps(data, indent=1),
		"method": event_mapper[event]
	}).insert(ignore_permissions=True)

	frappe.db.commit()
	frappe.enqueue(method=event_mapper[event], queue='short', timeout=300, is_async=True, 
		**{"order": data, "request_id": log.name})

@frappe.whitelist()
def resync(method, name, request_data):
	frappe.db.set_value("Shopify Log", name, "status", "Queued", update_modified=False)
	frappe.enqueue(method=method, queue='short', timeout=300, is_async=True, 
		**{"order": json.loads(request_data), "request_id": name})
