// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Order', {
	setup: function(frm) {
		frm.set_query("company_bank_account", function() {
			return {
				filters: {
					"is_company_account":1
				}
			}
		});
	},
	refresh: function(frm) {
		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Payment Request'), function() {
				frm.trigger("get_from_payment_request");
			}, __("Get Payments from"));

			frm.add_custom_button(__('Payment Entry'), function() {
				frm.trigger("get_from_payment_entry");
			}, __("Get Payments from"));

			frm.trigger('remove_button');
		}

		// payment Entry
		if (frm.doc.docstatus===1 && frm.doc.payment_order_type==='Payment Request') {
			frm.add_custom_button(__('Create Payment Entries'), function() {
				frm.trigger("make_payment_records");
			});
		}
	},

	remove_row_if_empty: function(frm) {
		// remove if first row is empty
		if (frm.doc.references.length > 0 && !frm.doc.references[0].reference_name) {
			frm.doc.references = [];
		}
	},

	remove_button: function(frm) {
		// remove custom button of order type that is not imported

		let label = ["Payment Request", "Payment Entry"];

		if (frm.doc.references.length > 0 && frm.doc.payment_order_type) {
			label = label.reduce(x => {
				x!= frm.doc.payment_order_type;
				return x;
			});
			frm.remove_custom_button(label, "Get from");
		}
	},

	get_from_payment_entry: function(frm) {
		frm.trigger("remove_row_if_empty");
		erpnext.utils.map_current_doc({
			method: "erpnext.accounts.doctype.payment_entry.payment_entry.make_payment_order",
			source_doctype: "Payment Entry",
			target: frm,
			date_field: "posting_date",
			setters: {
				party: frm.doc.supplier || ""
			},
			get_query_filters: {
				bank: frm.doc.bank,
				docstatus: 1,
				payment_type: ["!=", "Receive"],
				bank_account: frm.doc.company_bank_account,
				paid_from: frm.doc.account,
				payment_order_status: ["=", "Initiated"]
			}
		});
	},

	get_from_payment_request: function(frm) {
		frm.trigger("remove_row_if_empty");
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