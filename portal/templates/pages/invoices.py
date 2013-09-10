# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def get_context():
	from portal.website_transactions import get_currency_context
	context = get_currency_context()
	context.update({
		"title": "Invoices",
		"method": "portal.templates.pages.invoices.get_invoices",
		"icon": "icon-file-text",
		"empty_list_message": "No Invoices Found",
		"page": "invoice"
	})
	return context
	
@webnotes.whitelist()
def get_invoices(start=0):
	from portal.website_transactions import get_transaction_list
	return get_transaction_list("Sales Invoice", start)