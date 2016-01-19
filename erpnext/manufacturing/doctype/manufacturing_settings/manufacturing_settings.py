# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from dateutil.relativedelta import relativedelta

class ManufacturingSettings(Document):
	pass

def get_mins_between_operations():
	return relativedelta(minutes=cint(frappe.db.get_single_value("Manufacturing Settings",
		"mins_between_operations")) or 10)
