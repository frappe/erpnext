// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Partner Commission Payment', {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1) {
			frm.add_custom_button(__('Credit Note'), () => {
				frappe.call({
					method: "get_sales_invoice_data",
					doc: frm.doc,
					callback: function(r) {
						frappe.msgprint(__("Credit Note created in Sales Invoice Doctype"));
						frm.remove_custom_button('Credit Note', 'Create');
					}
				})
			}, __('Create'));
		}
		frm.add_custom_button(__("Get Commission Summary"), () => {
			frappe.call({
				method: "get_entries",
				doc: frm.doc,
				callback: function(r) {
					frm.clear_table("sales_order_table");
					frm.clear_table("delivery_note_table");
					frm.clear_table("sales_invoice_table");
					frm.refresh_fields();
					if(r.message) {
						var i;
						for(i = 0; i < r.message.length; i++) {
							if(frm.doc.based_on == "Sales Order") {
								var a = frm.add_child('sales_order_table');
								a.sales_order = r.message[i].name;
							} else if(frm.doc.based_on == "Delivery Note") {
								var a = frm.add_child('delivery_note_table');
								a.delivery_note = r.message[i].name;
							} else {
								var a = frm.add_child('sales_invoice_table');
								a.sales_invoice = r.message[i].name;
							}
							a.customer = r.message[i].customer;
							a.territory = r.message[i].territory;
							a.item_code = r.message[i].item_code;
							a.item_group = r.message[i].item_group;
							a.brand = r.message[i].brand;
							a.posting_date = r.message[i].posting_date;
							a.qty = r.message[i].qty;
							a.rate = r.message[i].rate;
							a.amount = r.message[i].amount;
							a.sales_partner = r.message[i].sales_partner;
							a.commission_rate = r.message[i].commission_rate;
							a.commission = r.message[i].commission;
							a.currency = r.message[i].currency;
							frm.refresh_field('sales_order_table');
							frm.refresh_field('delivery_note_table');
							frm.refresh_field('sales_invoice_table');
						}
					}
				}
			})
		});
	}
})
// Optimize later