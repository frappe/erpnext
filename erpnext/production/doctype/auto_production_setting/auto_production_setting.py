# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, cstr,getdate, nowtime
from erpnext.production.doctype.cop_rate.cop_rate import get_cop_rate
from erpnext.production.doctype.production.production import get_expense_account

class AutoProductionSetting(Document):
	pass
