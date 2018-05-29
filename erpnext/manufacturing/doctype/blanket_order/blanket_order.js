// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Blanket Order', {
	setup: function(frm) {
		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
	},

	refresh: function(frm) {
		if (frm.doc.customer && frm.doc.docstatus === 1) {
			frm.add_custom_button(__('View Orders'), function() {
				frappe.set_route('List', 'Sales Order', {blanket_order: frm.doc.name});
			});
			frm.add_custom_button(__("Create Sales Order"), function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_sales_order",
					frm: frm
				});
			}).addClass("btn-primary");
		}

		if (frm.doc.supplier && frm.doc.docstatus === 1) {
			frm.add_custom_button(__('View Orders'), function() {
				frappe.set_route('List', 'Purchase Order', {blanket_order: frm.doc.name});
			});
			frm.add_custom_button(__("Create Purchase Order"), function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_purchase_order",
					frm: frm
				});
			}).addClass("btn-primary");
		}
	}
});
