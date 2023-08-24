// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Putaway Rule', {
	setup: function(frm) {
		frm.set_query("warehouse", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"is_group": 0
				}
			};
		});
	},

	uom: function(frm) {
		if (frm.doc.item_code && frm.doc.uom) {
			return frm.call({
				method: "erpnext.stock.get_item_details.get_conversion_factor",
				args: {
					item_code: frm.doc.item_code,
					uom: frm.doc.uom
				},
				callback: function(r) {
					if (!r.exc) {
						let stock_capacity = flt(frm.doc.capacity) * flt(r.message.conversion_factor);
						frm.set_value('conversion_factor', r.message.conversion_factor);
						frm.set_value('stock_capacity', stock_capacity);
					}
				}
			});
		}
	},

	capacity: function(frm) {
		let stock_capacity = flt(frm.doc.capacity) * flt(frm.doc.conversion_factor);
		frm.set_value('stock_capacity', stock_capacity);
	}

	// refresh: function(frm) {

	// }
});
