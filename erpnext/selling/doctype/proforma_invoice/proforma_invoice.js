// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
{% include 'erpnext/selling/sales_common.js' %}


erpnext.selling.ProformaInvoiceController = class SalesOrderController extends erpnext.selling.SellingController {
	setup(frm) {
		super.setup();
		frm.custom_make_buttons = {
			'Delivery Note': 'Delivery Note',
			'Sales Invoice': 'Sales Invoice',
		}
	}

	refresh(frm) {
		super.refresh()
		// super.
		if (frm.docstatus==1) {
			const isDelivered = (item) => item.qty === item.delivered_qty
			const isInvoiced = (item) => item.qty === item.invoiced_qty

			!this.frm.doc.items.every(isInvoiced) &&
			this.frm.add_custom_button(__('Sales Invoice'), () => {
				this.make_sales_invoice(frm);
			}, __('Create'));

			!this.frm.doc.items.every(isDelivered) &&
				this.frm.add_custom_button(__('Delivery Note'), () => {
					this.make_delivery_note(frm);
				}, __('Create'));

		}
		this.frm.page.set_inner_btn_group_as_primary(__('Create'));
	}

	make_delivery_note() {
		this.frm.doc.items.forEach((item)=> item.qty === item.invoiced_qty && frappe.throw(__(`All Items already delivered for item ${item.item_name}`)))

		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
			frm: this.frm,
			args: {
				"doctype": "Proforma Invoice"
			}
		})
	}

	make_sales_invoice() {
		this.frm.doc.items.forEach((item)=> item.qty === item.delivered_qty && frappe.throw(__(`All Items already delivered for item ${item.item_name}`)))

		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			frm: this.frm,
			args: {
				"doctype": "Proforma Invoice"
			}
		})
	}
}
// erpnext/erpnext/selling/doctype/proforma_invoice/proforma_invoice.js
extend_cscript(cur_frm.cscript, new erpnext.selling.ProformaInvoiceController({frm: cur_frm}));

// frappe.ui.form.on("Proforma Invoice", {

// });
