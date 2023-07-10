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
			this.frm.add_custom_button(__('Sales Invoice'), () => {console.log("Clicked")
			}, __('Create'));
			this.frm.add_custom_button(__('Delivery Note'), () => this.make_proforma_invoice(), __('Create'));
		}

		this.frm.page.set_inner_btn_group_as_primary(__('Create'));

	}
	make_proforma_invoice() {
		console.log("Clicked Func")
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note_against_proforma_invoice",
			frm: this.frm,
		})
	}
}

extend_cscript(cur_frm.cscript, new erpnext.selling.ProformaInvoiceController({frm: cur_frm}));

// frappe.ui.form.on("Proforma Invoice", {

// });
