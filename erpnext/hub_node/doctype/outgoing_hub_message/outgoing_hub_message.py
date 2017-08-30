# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json, redis, re
from datetime import datetime
from frappe.utils import get_datetime_str
from frappe.model.document import Document
from erpnext.hub_node.doctype.hub_settings.hub_settings import hub_request

class OutgoingHubMessage(Document):
	def autoname(self):
		self.name = "OUT-" + self.type + '-' + re.sub('[^A-Za-z0-9]+', '-',
			get_datetime_str(datetime.now())[2:])

	def on_update(self):
		self.enqueue()

	def enqueue(self):
		enqueue_message(self.name, self.method, self.arguments, self.callback, self.callback_args, self.now)

def enqueue_message(message_id, method, data="", callback="", callback_args="", now=False):
	if now:
		hub_request(message_id, method, data, callback, callback_args)
		return
	try:
		frappe.enqueue('erpnext.hub_node.doctype.hub_settings.hub_settings.hub_request', now=now,
			message_id=message_id, api_method=method, data=data, callback=callback, callback_args=callback_args)
	except redis.exceptions.ConnectionError:
		hub_request(message_id, method, data, callback, callback_args)

def resend_failed_messages():
	max_tries = 10

def delete_oldest_successful_messages():
	pass
