# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from erpnext import get_default_company
from frappe.model.document import Document
from frappe.utils import nowdate


class ContractTemplate(Document):
	def validate(self):
		self.get_contract_sections()

	def get_contract_sections(self):
		contract_html = "<br>".join([section.description for section in self.contract_sections])
		self.contract_terms = contract_html
