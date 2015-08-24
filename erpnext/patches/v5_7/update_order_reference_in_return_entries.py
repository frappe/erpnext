# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# sales return
	return_entries = list(frappe.db.sql("""
		select dn.name as name, dn_item.name as row_id, dn.return_against, 
			dn_item.item_code, "Delivery Note" as doctype
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn_item.parent=dn.name and dn.is_return=1 and dn.docstatus < 2
	""", as_dict=1))
	
	return_entries += list(frappe.db.sql("""
		select si.name as name, si_item.name as row_id, si.return_against, 
			si_item.item_code, "Sales Invoice" as doctype
		from `tabSales Invoice Item` si_item, `tabSales Invoice` si
		where si_item.parent=si.name and si.is_return=1 and si.update_stock=1 and si.docstatus < 2
	""", as_dict=1))
	
	for d in return_entries:
		ref_field = "against_sales_order" if d.doctype == "Delivery Note" else "sales_order"
		order_details = frappe.db.sql("""
			select {0} as sales_order, so_detail 
			from `tab{1} Item` item
			where 
				parent=%s and item_code=%s 
				and ifnull(so_detail, '') !=''
			order by
				(select transaction_date from `tabSales Order` where name=item.{3}) DESC
		""".format(ref_field, d.doctype, ref_field, ref_field), (d.return_against, d.item_code), as_dict=1)
		
		if order_details:
			frappe.db.sql("""
				update `tab{0} Item`
				set {1}=%s, so_detail=%s
				where name=%s
			""".format(d.doctype, ref_field), 
			(order_details[0].sales_order, order_details[0].so_detail, d.row_id))
			
			doc = frappe.get_doc(d.doctype, d.name)
			doc.update_reserved_qty()
			
	
	#--------------------------
	# purchase return
	return_entries = frappe.db.sql("""
		select pr.name as name, pr_item.name as row_id, pr.return_against, pr_item.item_code
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr_item.parent=pr.name and pr.is_return=1 and pr.docstatus < 2
	""", as_dict=1)
	
	for d in return_entries:
		order_details = frappe.db.sql("""
			select prevdoc_docname as purchase_order, prevdoc_detail_docname as po_detail 
			from `tabPurchase Receipt Item` item
			where 
				parent=%s and item_code=%s 
				and ifnull(prevdoc_detail_docname, '') !='' 
				and ifnull(prevdoc_doctype, '') = 'Purchase Order' and ifnull(prevdoc_detail_docname, '') != ''
			order by
				(select transaction_date from `tabPurchase Order` where name=item.prevdoc_detail_docname) DESC
		""", (d.return_against, d.item_code), as_dict=1)
		
		if order_details:
			frappe.db.sql("""
				update `tabPurchase Receipt Item`
				set prevdoc_doctype='Purchase Order', prevdoc_docname=%s, prevdoc_detail_docname=%s
				where name=%s
			""", (order_details[0].purchase_order, order_details[0].po_detail, d.row_id))
			
			pr = frappe.get_doc("Purchase Receipt", d.name)
			pr.update_ordered_qty()
	