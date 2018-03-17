// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shipping Plan', {
	setup: function(frm) {
		frm.set_query('delivery_note', function(){
			return{
				filters: {
					'docstatus': 0
				}
			};
		});

		frm.set_query('company_address_name', function(){
			return {
				filters: {
					"is_your_company_address": 1
				}
			};
		});

		frm.set_query('weight_uom', 'items', function() {
			return {
				filters:{
					"name": ["in", ["LB", "Kg"]]
				}
			}
		});
	},
	company_address_name: function(frm) {
		erpnext.utils.get_address_display(frm, 'company_address_name', 'company_address', true);
	},
	shipping_address_name: function(frm) {
		erpnext.utils.get_address_display(frm, 'shipping_address_name', 'shipping_address', true);
	},
	set_total_handling_units: function(frm) {
		var total_qty = 0;
		$.each(frm.doc.items || [], function(idx, row) {
			total_qty += row.qty;
		});
		frm.set_value("total_handling_unit", total_qty);
	}
});

frappe.ui.form.on('Shipping Plan Item', {
	qty: function(frm, cdt, cdn) {
		frm.trigger("set_total_handling_units");
	},
	items_remove: function(frm, cdt, cdn) {
		frm.trigger("set_total_handling_units");
	}
})