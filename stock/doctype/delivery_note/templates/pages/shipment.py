# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

no_cache = True

def get_context():
	from portal.utils import get_transaction_context
	context = get_transaction_context("Delivery Note", webnotes.form_dict.name)
	context.update({
		"parent_link": "shipments",
		"parent_title": "Shipments"
	})
	return context