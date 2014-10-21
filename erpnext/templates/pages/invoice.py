# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, fmt_money
from shopping_cart.templates.utils import get_transaction_context

no_cache = 1
no_sitemap = 1

def get_context(context):
	invoice_context = frappe._dict({
		"parent_link": "invoices",
		"parent_title": "Invoices"
	})
	invoice_context.update(get_transaction_context("Sales Invoice", frappe.form_dict.name))
	modify_status(invoice_context.doc)
	return invoice_context
	
def modify_status(doc):
	doc.status = ""
	if flt(doc.outstanding_amount):
		doc.status = '<span class="label %s"><i class="icon-fixed-width %s"></i> %s</span>' % \
			("label-warning", "icon-exclamation-sign", 
			_("To Pay") + " = " + fmt_money(doc.outstanding_amount, currency=doc.currency))
	else:
		doc.status = '<span class="label %s"><i class="icon-fixed-width %s"></i> %s</span>' % \
			("label-success", "icon-ok", _("Paid"))
		