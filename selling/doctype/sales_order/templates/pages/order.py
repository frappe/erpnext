# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

no_cache = True

def get_context():
	from portal.utils import get_transaction_context
	context = get_transaction_context("Sales Order", webnotes.form_dict.name)
	context.update({
		"parent_link": "orders",
		"parent_title": "My Orders"
	})
	return context