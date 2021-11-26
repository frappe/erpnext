import json

import frappe


@frappe.whitelist()
def transaction_processing(data, to_create):
	deserialized_data = json.loads(data)
	length_of_data = len(deserialized_data)

	if length_of_data > 10:
		# frappe.msgprint("Started a background job to create {1} {0}".format(to_create,length_of_data))
		frappe.enqueue(job, deserialized_data=deserialized_data, to_create=to_create)
	else:
		job(deserialized_data, to_create)

def job(deserialized_data, to_create):
	from erpnext.accounts.doctype.payment_entry import payment_entry
	from erpnext.accounts.doctype.purchase_invoice import purchase_invoice
	from erpnext.accounts.doctype.sales_invoice import sales_invoice
	from erpnext.buying.doctype.purchase_order import purchase_order
	from erpnext.buying.doctype.supplier_quotation import supplier_quotation
	from erpnext.selling.doctype.quotation import quotation
	from erpnext.selling.doctype.sales_order import sales_order
	from erpnext.stock.doctype.delivery_note import delivery_note
	from erpnext.stock.doctype.purchase_receipt import purchase_receipt

	i = 0
	for d in deserialized_data:
		try:
			i+=1

			# From Sales Order
			if to_create == "Sales Invoice From Sales Order":
				si = sales_order.make_sales_invoice(d.get('name'))
				si.flags.ignore_validate = True
				si.insert(ignore_mandatory=True)

			if to_create == "Delivery Note From Sales Order":
				dn_so = sales_order.make_delivery_note(d.get('name'))
				si.flags.ignore_validate = True
				dn_so.insert(ignore_mandatory=True)

			if to_create == "Advance Payment From Sales Order":
				ap_so = payment_entry.get_payment_entry("Sales Order", d.get('name'))
				ap_so.flags.ignore_validate = True
				ap_so.insert(ignore_mandatory=True)

			# From Sales Invoice
			if to_create == "Delivery Note From Sales Invoice":
				dn_si = sales_invoice.make_delivery_note(d.get('name'))
				dn_si.flags.ignore_validate = True
				dn_si.insert(ignore_mandatory=True)

			if to_create == "Payment Sales Invoice":
				p_si = payment_entry.get_payment_entry("Sales Invoice", d.get('name'))
				p_si.flags.ignore_validate = True
				p_si.insert(ignore_mandatory=True)

			# From Delivery Note
			if to_create == "Sales Invoice From Delivery Note":
				si_from_dn = delivery_note.make_sales_invoice(d.get('name'))
				si_from_dn.flags.ignore_validate = True
				si_from_dn.insert(ignore_mandatory=True)

			if to_create == "Packaging Slip From Delivery Note":
				ps  = delivery_note.make_packing_slip(d.get('name'))
				ps.flags.ignore_validate = True
				ps.insert(ignore_mandatory=True)

			# From Quotation
			if to_create == "Sales Order From Quotation":
				so_qtn = quotation._make_sales_order(d.get('name'))
				so_qtn.flags.ignore_validate = True
				so_qtn.insert(ignore_mandatory=True)

			if to_create == "Sales Invoice From Quotation":
				si_qtn = quotation._make_sales_invoice(d.get('name'))
				si_qtn.flags.ignore_validate = True
				si_qtn.insert(ignore_mandatory=True)

			# From Supplier Quotation
			if to_create == "Purchase Order From Supplier Quotation":
				po_sq = supplier_quotation.make_purchase_order(d.get('name'))
				po_sq.flags.ignore_validate = True
				po_sq.insert(ignore_mandatory=True)

			if to_create == "Purchase Invoice From Supplier Quotation":
				# created method to create purchase invoice from supplier quotation
				pi_sq = supplier_quotation.make_purchase_invoice(d.get('name'))
				pi_sq.flags.ignonre_validate = True
				pi_sq.insert(ignore_mandatory=True)

			# From Purchase Order
			if to_create == "Purchase Invoice From Purchase Order":
				pi_po = purchase_order.get_mapped_purchase_invoice(d.get('name'))
				pi_po.flags.ignore_validate = True
				pi_po.insert(ignore_mandatory=True)

			if to_create == "Purchase Receipt From Purchase Order":
				pr_po = purchase_order.make_purchase_receipt(d.get('name'))
				pr_po.flags.ignore_validate = True
				pr_po.insert(ignore_mandatory=True)

			if to_create == "Advance Payment From Purchase Order":
				ap_po = payment_entry.get_payment_entry("Purchase Order", d.get('name'))
				ap_po.flags.ignore_validate = True
				ap_po.insert(ignore_mandatory=True)

			# From Purchase Invoice
			if to_create == "Purchase Receipt From Purchase Invoice":
				pr_pi = purchase_invoice.make_purchase_receipt(d.get('name'))
				pr_pi.flags.ignore_valdiate = True
				pr_pi.insert(ignore_mandatory=True)

			if to_create == "Payment Purchase Invoice":
				p_pi = payment_entry.get_payment_entry("Purchase Invoice", d.get("name"))
				p_pi.flags.ignore_validate = True
				p_pi.insert(ignore_mandatory=True)

			# From Purchase Receipt
			if to_create == "Purchase Invoice From Purchase Receipt":
				pr_pi = purchase_receipt.make_purchase_invoice(d.get('name'))
				pr_pi.flags.ignore_validate = True
				pr_pi.insert(ignore_mandatory=True)

		except Exception as e:
			frappe.msgprint("Error while creating {1} from {0}".format(d.get('name'), to_create), title="Invoice Creation Failed")
