// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Order', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Payment Request'), function() {
				frm.trigger("get_from_payment_request");
			}, __("Get from"));
		}

		// payment Entry
		if (frm.doc.docstatus==1) {
			frm.add_custom_button(__('Make Payment Entries'),
				function() { 
					frm.trigger("make_payment_records")
			});
		}
	},

	get_from_payment_request: function(frm) {
		erpnext.utils.map_current_doc({
			method: "erpnext.accounts.doctype.payment_request.payment_request.make_payment_order",
			source_doctype: "Payment Request",
			target: frm,
			setters: {
				party: frm.doc.supplier || ""
			},
			get_query_filters: {
				bank: frm.doc.bank,
				docstatus: 1,
				status: ["=", "Initiated"],
			}
		});
	},

	make_payment_records: function(frm){
		var dialog = new frappe.ui.Dialog({
			title: __("For Supplier"),
			fields: [
				{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier",
					"get_query": function () {
						return {
							query:"erpnext.accounts.doctype.payment_order.payment_order.get_supplier_query",
							filters: {'parent': frm.doc.name}
						}
					}, "reqd": 1
				},

				{"fieldtype": "Link", "label": __("Mode of Payment"), "fieldname": "mode_of_payment", "options":"Mode of Payment",
					"get_query": function () {
						return {
							query:"erpnext.accounts.doctype.payment_order.payment_order.get_mop_query",
							filters: {'parent': frm.doc.name}
						}
					}
				}
			]
		});

		dialog.set_primary_action(__("Submit"), function() {
			var args = dialog.get_values();
			if(!args) return;

			return frappe.call({
				method: "erpnext.accounts.doctype.payment_order.payment_order.make_payment_records",
				args: {
					"name": me.frm.doc.name,
					"supplier": args.supplier,
					"mode_of_payment": args.mode_of_payment
				},
				freeze: true,
				callback: function(r) {
					dialog.hide();
					frm.refresh();
				}
			})
		})

		dialog.show();
	},
	
});
