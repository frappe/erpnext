from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	# Move Landed Cost Taxes and Charges in Stock Entry to Stock Entry Taxes and Charges
	frappe.db.sql("""
		create table `tabStock Entry Taxes and Charges`
		as select * from `tabLanded Cost Taxes and Charges`
		where parenttype='Stock Entry'
	""")
	frappe.db.sql("delete from `tabLanded Cost Taxes and Charges` where parenttype='Stock Entry'")

	# Rename LCV fields
	frappe.reload_doc('stock', 'doctype', 'landed_cost_voucher')
	frappe.reload_doc('stock', 'doctype', 'landed_cost_taxes_and_charges')
	frappe.reload_doc('stock', 'doctype', 'landed_cost_item')

	# Landed Cost Taxes and Charges table description to remarks
	rename_field("Landed Cost Taxes and Charges", "description", "remarks")

	# Landed Cost distribution criteria from LCV to Taxes table
	frappe.db.sql("""
		update `tabLanded Cost Taxes and Charges` t
		inner join `tabLanded Cost Voucher` v on v.name = t.parent
		set t.distribution_criteria = v.distribute_charges_based_on
	""")

	# Landed Cost Voucher status
	frappe.db.sql("""
		update `tabLanded Cost Voucher` set status = (case
			when docstatus=0 then 'Draft'
			when docstatus=1 then 'Submitted'
			when docstatus=2 then 'Cancelled'
		end)
	""")

	# Landed Cost Item table
	# weight, po, po_item, pr, pr_item, pi, pi_item, manual_distribution
	lcv_items = frappe.db.sql("""select name, item_code, receipt_document_type, receipt_document, purchase_receipt_item
		from `tabLanded Cost Item`""", as_dict=1)

	for d in lcv_items:
		changes = frappe._dict()
		changes.manual_distribution = "{}"

		if d.receipt_document_type == "Purchase Receipt":
			changes.purchase_receipt = d.receipt_document
			changes.purchase_receipt_item = d.purchase_receipt_item
		elif d.receipt_document_type == "Purchase Invoice":
			changes.purchase_invoice = d.receipt_document
			changes.purchase_invoice_item = d.purchase_receipt_item
		else:
			continue

		pr_item = None
		if d.purchase_receipt_item:
			pr_item = frappe.db.sql("""
				select purchase_order, {po_detail_field} as po_detail, total_weight
				from `tab{dt} Item`
				where name = %s
			""".format(  # nosec
				po_detail_field="purchase_order_item" if d.receipt_document_type == "Purchase Receipt" else "po_detail",
				dt=d.receipt_document_type
			), d.purchase_receipt_item, as_dict=1)

		if pr_item:
			pr_item = pr_item[0]
			changes.purchase_order = pr_item.purchase_order
			changes.purchase_order_item = pr_item.po_detail
			changes.weight = pr_item.total_weight

		frappe.db.set_value("Landed Cost Item", d.name, changes, None, update_modified=False)
