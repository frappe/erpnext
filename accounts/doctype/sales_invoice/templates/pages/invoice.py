# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import flt, fmt_money

no_cache = True

def get_context():
	from portal.utils import get_transaction_context
	context = get_transaction_context("Sales Invoice", webnotes.form_dict.name)
	modify_status(context.get("doc"))
	context.update({
		"parent_link": "invoices",
		"parent_title": "Invoices"
	})
	return context
	
def modify_status(doc):
	doc.status = ""
	if flt(doc.outstanding_amount):
		doc.status = '<span class="label %s"><i class="icon-fixed-width %s"></i> %s</span>' % \
			("label-warning", "icon-exclamation-sign", 
			_("To Pay") + " = " + fmt_money(doc.outstanding_amount, currency=doc.currency))
	else:
		doc.status = '<span class="label %s"><i class="icon-fixed-width %s"></i> %s</span>' % \
			("label-success", "icon-ok", _("Paid"))
		