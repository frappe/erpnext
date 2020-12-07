# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.jinja import validate_template
from six import string_types
import json

class ContractTemplate(Document):
	def validate(self):
		if self.contract_terms:
			validate_template(self.contract_terms)

@frappe.whitelist()
def get_contract_template(template_name, doc):
	if isinstance(doc, string_types):
		doc = json.loads(doc)

	contract_template = frappe.get_doc("Contract Template", template_name)
	contract_terms = None

	if contract_template.contract_terms:
		contract_terms = frappe.render_template(contract_template.contract_terms, doc)
	
	return {
		'contract_template': contract_template, 
		'contract_terms': contract_terms
	}