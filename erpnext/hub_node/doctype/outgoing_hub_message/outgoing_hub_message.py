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
		enqueue_message(self.method, self.arguments, self.callback, self.callback_args, self.name, self.now)

def enqueue_message(method, data="", callback="", callback_args="", message_id="", now=False):
	if now:
		hub_request(method, data, callback, callback_args, message_id)
		return
	try:
		frappe.enqueue('erpnext.hub_node.doctype.hub_settings.hub_settings.hub_request', now=now,
			api_method=method, data=data, callback=callback, callback_args=callback_args, message_id=message_id)
	except redis.exceptions.ConnectionError:
		hub_request(method, data, callback, callback_args, message_id)

def resend_failed_messages():
	max_tries = 10

def delete_oldest_successful_messages():
	pass
