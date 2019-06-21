// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.toggle_enable('new_item_code', doc.__islocal);
}

cur_frm.fields_dict.new_item_code.get_query = function() {
	return{
		query: "erpnext.selling.doctype.product_bundle.product_bundle.get_new_item_code"
	}
}
cur_frm.fields_dict.new_item_code.query_description = __('Please select Item where "Is Stock Item" is "No" and "Is Sales Item" is "Yes" and there is no other Product Bundle');

cur_frm.cscript.onload = function() {
	// set add fetch for item_code's item_name and description
	cur_frm.add_fetch('item_code', 'stock_uom', 'uom');
	cur_frm.add_fetch('item_code', 'description', 'description');
}

frappe.ui.form.on('Product Bundle', {
	set_total_weightage: function(frm, cdt, cdn) {
		if(isNaN(locals[cdt][cdn].weightage_per_qty)){
			frappe.model.set_value(cdt, cdn, 'total_weightage', 0.0 );
		}
		else if(isNaN(locals[cdt][cdn].qty)) {
			frappe.model.set_value(cdt, cdn, 'total_weightage', 0.0 );
		}
		else {
			frappe.model.set_value(cdt, cdn, 'total_weightage', locals[cdt][cdn].weightage_per_qty * locals[cdt][cdn].qty);
		}
	},
});

frappe.ui.form.on('Product Bundle Item', {
	qty: function(frm, cdt, cdn) {
		frm.events.set_total_weightage(frm, cdt, cdn);
	},

	weightage_per_qty: function(frm, cdt, cdn) {
		frm.events.set_total_weightage(frm, cdt, cdn);
	},
});