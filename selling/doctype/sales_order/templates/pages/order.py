# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

no_cache = True

def get_context():
	from portal.utils import get_transaction_context
	context = get_transaction_context("Sales Order", webnotes.form_dict.name)
	if context.get("doc").get("name") != "Not Allowed":
		modify_status(context.get("doc"))
		context.update({
			"parent_link": "orders",
			"parent_title": "My Orders"
		})
	return context
	
def modify_status(doc):
	doc.status = []
	if 0 < doc.per_billed < 100:
		doc.status.append(("label-warning", "icon-ok", _("Partially Billed")))
	elif doc.per_billed == 100:
		doc.status.append(("label-success", "icon-ok", _("Billed")))
	
	if 0 < doc.per_delivered < 100:
		doc.status.append(("label-warning", "icon-truck", _("Partially Delivered")))
	elif doc.per_delivered == 100:
		doc.status.append(("label-success", "icon-truck", _("Delivered")))
	doc.status = " " + " ".join(('<span class="label %s"><i class="icon-fixed-width %s"></i> %s</span>' % s 
			for s in doc.status))
