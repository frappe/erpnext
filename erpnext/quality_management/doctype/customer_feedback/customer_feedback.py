# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CustomerFeedback(Document):
	
	def create_action(self):
		if len(self.feedback) != 0:
			query = frappe.get_list("Quality Action", filters={"feedback": ""+ self.name +""})
			if len(query) == 0:
				doc = frappe.get_doc({
					'doctype': 'Quality Action',
					'action': 'Corrective',
					'type': 'Customer Feedback',
					'feedback': ''+ self.name +'',
					'date': ''+ frappe.utils.nowdate() +''
				})
				for data in self.feedback:
					print(data)
					doc.append("description",{
						'problem': data.parameter + '-' +data.qualitative_feedback,
						'status': 'Open'
					})
				doc.insert()
				frappe.db.commit()
			else:
				pass
			return "Action Initialized"
		else:
			return "Action Not Initalized"