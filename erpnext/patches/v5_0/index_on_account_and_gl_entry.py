from __future__ import unicode_literals

import frappe

def execute():
	index_map = {
		"Account": ["parent_account", "lft", "rgt"],
		"GL Entry": ["posting_date", "account", 'party', "voucher_no"]
	}
	
	for dt, indexes in index_map.items():
		existing_indexes = [d.Key_name for d in frappe.db.sql("""show index from `tab{0}` 
			where Column_name != 'name'""".format(dt), as_dict=1)]

		for old in existing_indexes:
			if old in ("parent", "group_or_ledger", "is_pl_account", "debit_or_credit", "account_name", "company"):
				frappe.db.sql("alter table `tab{0}` drop index {1}".format(dt, old))
				existing_indexes.remove(old)
							
		for new in indexes:
			if new not in existing_indexes:
				frappe.db.sql("alter table `tab{0}` add index ({1})".format(dt, new))