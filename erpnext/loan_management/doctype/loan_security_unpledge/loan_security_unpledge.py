# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime

class LoanSecurityUnpledge(Document):
	pass

@frappe.whitelist()
def approve_unpledge_request(loan, unpledge_request):
	frappe.db.sql("""UPDATE `tabLoan Security Unpledge`
		SET unpledge_status = "Unpledged", unpledge_time = %s
		WHERE name = %s""", (get_datetime(), unpledge_request))

	frappe.db.set_value("Loan", loan, "status", "Repaid/Closed")