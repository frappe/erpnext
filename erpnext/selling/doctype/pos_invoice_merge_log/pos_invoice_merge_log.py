# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt, add_months, today, date_diff, getdate, add_days, cstr, nowdate
from frappe.model.document import Document

class POSInvoiceMergeLog(Document):
	pass
