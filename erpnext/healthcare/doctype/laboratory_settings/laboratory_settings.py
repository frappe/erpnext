# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document

class LaboratorySettings(Document):
	def validate(self):
		for key in ["require_test_result_approval","require_sample_collection"]:
			frappe.db.set_default(key, self.get(key, ""))

@frappe.whitelist()
def get_sms_text(doc):
	sms_text = {}
	doc = frappe.get_doc("Lab Test",doc)
	#doc = json.loads(doc)
	context = {"doc": doc, "alert": doc, "comments": None}
	emailed = frappe.db.get_value("Laboratory Settings", None, "sms_emailed")
	sms_text['emailed'] = frappe.render_template(emailed, context)
 	printed = frappe.db.get_value("Laboratory Settings", None, "sms_printed")
	sms_text['printed'] = frappe.render_template(printed, context)
	return sms_text
