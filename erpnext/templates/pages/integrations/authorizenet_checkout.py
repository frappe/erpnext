# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import fmt_money


def get_context(context):
	payment_context = dict(frappe.local.request.args)
	context.payment_context = payment_context
	context["amount"] = fmt_money(amount=payment_context.get('amount'), currency=payment_context.get('currency'))
