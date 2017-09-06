# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.model.document import Document

class HubMessage(Document):
	def on_update(self):
		if self.now:
			self.run()
		else:
			frappe.enqueue('erpnext.hub_node.doctype.hub_message.hub_message.enqueue', message_id=self.name)

	def run(self):
		hub = frappe.get_single("Hub Settings")
		data = json.loads(self.data)
		data['access_token'] = hub.access_token
		self.response = requests.post(hub.get_hub_url() + "/api/method/hub.hub.api." + self.method,
			data = data)

		self.http_status_code = self.response.status_code

		if self.response.ok:
			self.status = 'Success'
			self.response_text = self.response.content
			self.save()
			if self.callback:
				callback_args = json.loads(self.callback_args)
				callback_args['hub_message'] = self

				frappe.call(self.callback, **callback_args)
		else:
			self.status = 'Failed'
			self.save()

@frappe.whitelist()
def resend(message):
	message = frappe.get_doc('Hub Message', message)
	if message.has_permission() and message.status=='Pending':
		message.enqueue()

def enqueue(message_id):
	frappe.get_doc('Hub Message', message_id).run()
