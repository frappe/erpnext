// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
{% include 'erpnext/selling/sales_common.js' %}


erpnext.selling.ProformaInvoiceController = class SalesOrderController extends erpnext.selling.SellingController {
	setup(frm) {
		super.setup();
		console.log(frm)
	}
	refresh(frm) {
	}
}

extend_cscript(cur_frm.cscript, new erpnext.selling.ProformaInvoiceController({frm: cur_frm}));

// frappe.ui.form.on("Proforma Invoice", {

// });
