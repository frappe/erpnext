// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Blanket Order', {
	onload: function(frm) {
		frm.trigger('set_tc_name_filter');
	},

	setup: function(frm) {
		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
	},

	refresh: function(frm) {
		erpnext.hide_company();
		if (frm.doc.customer && frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Sales Order"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_order",
					frm: frm,
					args: {
						doctype: 'Sales Order'
					}
				});
			}, __('Create'));

			frm.add_custom_button(__("Quotation"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_order",
					frm: frm,
					args: {
						doctype: 'Quotation'
					}
				});
			}, __('Create'));
		}

		if (frm.doc.supplier && frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Purchase Order"), function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_order",
					frm: frm,
					args: {
						doctype: 'Purchase Order'
					}
				});
			}, __('Create'));
		}
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	tc_name: function (frm) {
		erpnext.utils.get_terms(frm.doc.tc_name, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("terms", r.message);
			}
		});
	},

	set_tc_name_filter: function(frm) {
		if (frm.doc.blanket_order_type === 'Selling') {
			frm.set_df_property("customer","reqd", 1);
			frm.set_df_property("supplier","reqd", 0);
			frm.set_value("supplier", "");

			frm.set_query("tc_name", function() {
				return { filters: { selling: 1 } };
			});
		}
		if (frm.doc.blanket_order_type === 'Purchasing') {
			frm.set_df_property("supplier","reqd", 1);
			frm.set_df_property("customer","reqd", 0);
			frm.set_value("customer", "");

			frm.set_query("tc_name", function() {
				return { filters: { buying: 1 } };
			});
		}
	},

	blanket_order_type: function (frm) {
		frm.trigger('set_tc_name_filter');
	}
});


