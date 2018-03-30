# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import print_function, unicode_literals
import frappe

"""
This patch is written to fix Stock Ledger Entries and GL Entries 
against Delivery Notes and Sales Invoice where Target Warehouse has been set wrongly
due to User Permissions on Warehouse.

This cannot be run automatically because we can't take a call that 
Target Warehouse has been set purposefully or by mistake. 
Thats why we left it to the users to take the call, and manually run the patch.

This patch has 2 main functions, `check()` and `repost()`. 
- Run `check` function, to list out all the Sales Orders, Delivery Notes 
	and Sales Invoice with Target Warehouse.
- Run `repost` function to remove the Target Warehouse value and repost SLE and GLE again.

To execute this patch run following commands from frappe-bench directory:
```
	bench --site [your-site-name] execute erpnext.patches.v6_12.repost_entries_with_target_warehouse.check
	bench --site [your-site-name] backup
	bench --site [your-site-name] execute erpnext.patches.v6_12.repost_entries_with_target_warehouse.repost
```

Exception Handling:
While reposting, if you get any exception, it will printed on screen. 
Mostly it can be due to negative stock issue. If that is the case, follow these steps
	- Ensure that stock is available for those items in the mentioned warehouse on the date mentioned in the error
	- Execute `repost` funciton again
"""

def check():
	so_list = get_affected_sales_order()
	dn_list = get_affected_delivery_notes()
	si_list = get_affected_sales_invoice()
	
	if so_list or dn_list or si_list:
		print("Entries with Target Warehouse:")
		
		if so_list:
			print("Sales Order")
			print(so_list)

		if dn_list:
			print("Delivery Notes")
			print([d.name for d in dn_list])

		if si_list:
			print("Sales Invoice")
			print([d.name for d in si_list])
		
		
def repost():
	dn_failed_list, si_failed_list = [], []
	repost_dn(dn_failed_list)
	repost_si(si_failed_list)
	repost_so()
	frappe.db.commit()
	
	if dn_failed_list:
		print("-"*40)
		print("Delivery Note Failed to Repost")
		print(dn_failed_list)

	if si_failed_list:
		print("-"*40)
		print("Sales Invoice Failed to Repost")
		print(si_failed_list)
		print()
		
		print("""
If above Delivery Notes / Sales Invoice failed due to negative stock, follow these steps:
	- Ensure that stock is available for those items in the mentioned warehouse on the date mentioned in the error
	- Run this patch again
""")
	
def repost_dn(dn_failed_list):
	dn_list = get_affected_delivery_notes()
		
	if dn_list:
		print("-"*40)
		print("Reposting Delivery Notes")

	for dn in dn_list:
		if dn.docstatus == 0:
			continue
			
		print(dn.name)
	
		try:
			dn_doc = frappe.get_doc("Delivery Note", dn.name)
			dn_doc.docstatus = 2
			dn_doc.update_prevdoc_status()
			dn_doc.update_stock_ledger()
			dn_doc.cancel_packing_slips()
			frappe.db.sql("""delete from `tabGL Entry` 
				where voucher_type='Delivery Note' and voucher_no=%s""", dn.name)

			frappe.db.sql("update `tabDelivery Note Item` set target_warehouse='' where parent=%s", dn.name)
			dn_doc = frappe.get_doc("Delivery Note", dn.name)
			dn_doc.docstatus = 1
			dn_doc.on_submit()
			frappe.db.commit()
		except Exception:
			dn_failed_list.append(dn.name)
			frappe.local.stockledger_exceptions = None
			print(frappe.get_traceback())
			frappe.db.rollback()
		
	frappe.db.sql("update `tabDelivery Note Item` set target_warehouse='' where docstatus=0")

def repost_si(si_failed_list):
	si_list = get_affected_sales_invoice()

	if si_list:
		print("-"*40)
		print("Reposting Sales Invoice")
	
	for si in si_list:
		if si.docstatus == 0:
			continue
		
		print(si.name)
	
		try:
			si_doc = frappe.get_doc("Sales Invoice", si.name)
			si_doc.docstatus = 2
			si_doc.update_stock_ledger()
			frappe.db.sql("""delete from `tabGL Entry` 
				where voucher_type='Sales Invoice' and voucher_no=%s""", si.name)
			
			frappe.db.sql("update `tabSales Invoice Item` set target_warehouse='' where parent=%s", si.name)
			si_doc = frappe.get_doc("Sales Invoice", si.name)
			si_doc.docstatus = 1
			si_doc.update_stock_ledger()
			si_doc.make_gl_entries()
			frappe.db.commit()
		except Exception:
			si_failed_list.append(si.name)
			frappe.local.stockledger_exceptions = None
			print(frappe.get_traceback())
			frappe.db.rollback()
		
	frappe.db.sql("update `tabSales Invoice Item` set target_warehouse='' where docstatus=0")
	
def repost_so():
	so_list = get_affected_sales_order()
	
	frappe.db.sql("update `tabSales Order Item` set target_warehouse=''")
	
	if so_list:
		print("-"*40)
		print("Sales Order reposted")
	
	
def get_affected_delivery_notes():
	return frappe.db.sql("""select distinct dn.name, dn.docstatus
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where dn.name=dn_item.parent and dn.docstatus < 2
			and dn_item.target_warehouse is not null and dn_item.target_warehouse != '' 
		order by dn.posting_date asc""", as_dict=1)
			
def get_affected_sales_invoice():
	return frappe.db.sql("""select distinct si.name, si.docstatus
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si.name=si_item.parent and si.docstatus < 2 and si.update_stock=1
			and si_item.target_warehouse is not null and si_item.target_warehouse != '' 
		order by si.posting_date asc""", as_dict=1)
		
def get_affected_sales_order():
	return frappe.db.sql_list("""select distinct parent from `tabSales Order Item` 
		where target_warehouse is not null and target_warehouse != '' and docstatus <2""")