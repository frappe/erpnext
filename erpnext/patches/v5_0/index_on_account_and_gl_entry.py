from __future__ import unicode_literals

import frappe

def execute():
	index_map = {
		"Account": ["parent_account", "lft", "rgt"],
		"GL Entry": ["posting_date", "account", 'party', "voucher_no"],
		"Sales Invoice": ["posting_date", "debit_to", "customer"],
		"Purchase Invoice": ["posting_date", "credit_to", "supplier"]
	}
	
	for dt, indexes in index_map.items():
		existing_indexes = [(d.Key_name, d.Column_name) for d in frappe.db.sql("""show index from `tab{0}` 
			where Column_name != 'name'""".format(dt), as_dict=1)]

		for old, column in existing_indexes:
			if column in ("parent", "group_or_ledger", "is_group", "is_pl_account", "debit_or_credit", 
					"account_name", "company", "project", "voucher_date", "due_date", "bill_no", 
					"bill_date", "is_opening", "fiscal_year", "outstanding_amount"):
				frappe.db.sql("alter table `tab{0}` drop index {1}".format(dt, old))
		
		existing_indexes = [(d.Key_name, d.Column_name) for d in frappe.db.sql("""show index from `tab{0}` 
			where Column_name != 'name'""".format(dt), as_dict=1)]
			
		existing_indexed_columns = list(set([x[1] for x in existing_indexes]))
							
		for new in indexes:
			if new not in existing_indexed_columns:
				frappe.db.sql("alter table `tab{0}` add index ({1})".format(dt, new))