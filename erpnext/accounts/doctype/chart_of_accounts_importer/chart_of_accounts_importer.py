# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ChartofAccountsImporter(Document):
	pass

@frappe.whitelist()
def validate_company(company):
	if frappe.db.get_all('GL Entry', {"company": company}, "name", limit=1):
		return False	
