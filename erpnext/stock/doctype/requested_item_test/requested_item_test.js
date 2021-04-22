// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Requested_item_test', {
	// refresh: function(frm) {

	// }
	calculate_supply: function(frm) {
		let total_supply = 0;
		for(let i in frm.doc.vendors_stock){
			if(frm.doc.vendors_stock[i].available_quantity >= frm.doc.vendors_stock[i].supply && frm.doc.vendors_stock[i].supply >= 0)
				total_supply = total_supply + frm.doc.vendors_stock[i].supply;
			else
				frappe.throw(__("Invalid supply quantity."));
		}
		frm.set_value("supply_quantity", total_supply);
	},

	before_submit: function(frm) {
		if(frm.doc.requested_quantity != frm.doc.supply_quantity){
			frappe.throw(__("Supply Quantity is not matching Requested quantity."));
		}
	}
});

frappe.ui.form.on('Warehouse_vendors_stock_test', {
	supply: function(frm) {
		frm.trigger("calculate_supply");
	}
});
