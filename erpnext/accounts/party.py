# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes
from webnotes import _

@webnotes.whitelist()
def get_party_details(party=None, account=None, party_type="Customer"):
	if not webnotes.has_permission(party_type, "read", party):
		webnotes.throw("No Permission")
	
	if party_type=="Customer":
		get_party_details = webnotes.get_attr("erpnext.selling.doctype.customer.customer.get_customer_details")
	else:
		get_party_details = webnotes.get_attr("erpnext.buying.doctype.supplier.supplier.get_supplier_details")
				
	if party:
		account = get_party_account(company, party, party_type)
	elif account:
		party = webnotes.conn.get_value('Account', account, 'master_name')

	account_fieldname = "debit_to" if party_type=="Customer" else "credit_to" 

	out = {
		party_type.lower(): party,
		account_fieldname : account,
		"due_date": get_due_date(posting_date, party, party_type, account, company)
	}	
	out.update(get_party_details(party))
	return out

def get_party_account(company, party, party_type):
	if not company:
		webnotes.throw(_("Please select company first."))

	if party:
		acc_head = webnotes.conn.get_value("Account", {"master_name":party,
			"master_type": party_type, "company": company})

		if not acc_head:
			create_party_account(party, party_type, company)
	
		return acc_head		

def get_due_date(posting_date, party, party_type, account, company):
	"""Set Due Date = Posting Date + Credit Days"""
	due_date = None
	if posting_date:
		credit_days = 0
		if debit_to:
			credit_days = webnotes.conn.get_value("Account", account, "credit_days")
		if party and not credit_days:
			credit_days = webnotes.conn.get_value(party_type, party, "credit_days")
		if company and not credit_days:
			credit_days = webnotes.conn.get_value("Company", company, "credit_days")
			
		due_date = add_days(posting_date, credit_days) if credit_days else posting_date

	return due_date	

def create_party_account(party, party_type, company):
	if not company:
		webnotes.throw(_("Company is required"))
		
	company_details = webnotes.conn.get_value("Company", company, 
		["abbr", "receivables_group", "payables_group"], as_dict=True)
	if not webnotes.conn.exists("Account", (party + " - " + abbr)):
		parent_account = company_details.receivables_group \
			if party_type=="Customer" else company_details.payables_group

		# create
		account = webnotes.bean({
			"doctype": "Account",
			'account_name': party,
			'parent_account': parent_account, 
			'group_or_ledger':'Ledger',
			'company': company, 
			'master_type': party_type, 
			'master_name': party,
			"freeze_account": "No"
		}).insert(ignore_permissions=True)
		
		msgprint(_("Account Created") + ": " + account.doc.name)
