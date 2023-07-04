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
			this.frm.add_custom_button(__('Delivery Note'), () => {console.log("Clicked")}, __('Create'));
		}
		this.frm.page.set_inner_btn_group_as_primary(__('Create'));

	}

}

extend_cscript(cur_frm.cscript, new erpnext.selling.ProformaInvoiceController({frm: cur_frm}));

// frappe.ui.form.on("Proforma Invoice", {

// });
