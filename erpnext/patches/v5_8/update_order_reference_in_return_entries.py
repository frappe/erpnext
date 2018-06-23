# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Delivery Note")
	frappe.reload_doctype("Sales Invoice")
	frappe.reload_doctype("Purchase Receipt")
	frappe.reload_doctype("Sales Order Item")
	frappe.reload_doctype("Purchase Order Item")
	frappe.reload_doctype("Purchase Order Item Supplied")

	# sales return
	return_entries = list(frappe.db.sql("""
		select dn.name as name, dn_item.name as row_id, dn.return_against,
			dn_item.item_code, "Delivery Note" as doctype
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn_item.parent=dn.name and dn.is_return=1 and dn.docstatus < 2
	""", as_dict=1))

	return_entries += list(frappe.db.sql("""
		select si.name as name, si_item.name as row_id, si.return_against,
			si_item.item_code, "Sales Invoice" as doctype, update_stock
		from `tabSales Invoice Item` si_item, `tabSales Invoice` si
		where si_item.parent=si.name and si.is_return=1 and si.docstatus < 2
	""", as_dict=1))

	for d in return_entries:
		ref_field = "against_sales_order" if d.doctype == "Delivery Note" else "sales_order"
		order_details = frappe.db.sql("""
			select {ref_field} as sales_order, so_detail,
				(select transaction_date from `tabSales Order` where name=item.{ref_field}) as sales_order_date
			from `tab{doctype} Item` item
			where
				parent=%s
				and item_code=%s
				and ifnull(so_detail, '') !=''
			order by sales_order_date DESC limit 1
		""".format(ref_field=ref_field, doctype=d.doctype), (d.return_against, d.item_code), as_dict=1)

		if order_details:
			frappe.db.sql("""
				update `tab{doctype} Item`
				set {ref_field}=%s, so_detail=%s
				where name=%s
			""".format(doctype=d.doctype, ref_field=ref_field),
			(order_details[0].sales_order, order_details[0].so_detail, d.row_id))

			if (d.doctype=="Sales Invoice" and d.update_stock) or d.doctype=="Delivery Note":
				doc = frappe.get_doc(d.doctype, d.name)
				doc.update_reserved_qty()

				if d.doctype=="Sales Invoice":
					doc.status_updater = []
					doc.update_status_updater_args()

				doc.update_prevdoc_status()

	#--------------------------
	# purchase return
	return_entries = frappe.db.sql("""
		select pr.name as name, pr_item.name as row_id, pr.return_against, pr_item.item_code
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr_item.parent=pr.name and pr.is_return=1 and pr.docstatus < 2
	""", as_dict=1)

	for d in return_entries:
		order_details = frappe.db.sql("""
			select prevdoc_docname as purchase_order, prevdoc_detail_docname as po_detail,
				(select transaction_date from `tabPurchase Order` where name=item.prevdoc_detail_docname) as purchase_order_date
			from `tabPurchase Receipt Item` item
			where
				parent=%s
				and item_code=%s
				and ifnull(prevdoc_detail_docname, '') !=''
				and ifnull(prevdoc_doctype, '') = 'Purchase Order' and ifnull(prevdoc_detail_docname, '') != ''
			order by purchase_order_date DESC limit 1
		""", (d.return_against, d.item_code), as_dict=1)

		if order_details:
			frappe.db.sql("""
				update `tabPurchase Receipt Item`
				set prevdoc_doctype='Purchase Order', prevdoc_docname=%s, prevdoc_detail_docname=%s
				where name=%s
			""", (order_details[0].purchase_order, order_details[0].po_detail, d.row_id))

			pr = frappe.get_doc("Purchase Receipt", d.name)
			pr.update_ordered_and_reserved_qty()
			pr.update_prevdoc_status()

