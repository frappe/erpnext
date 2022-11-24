// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Coal Raising Payment', {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1 ){
			if(frappe.model.can_read("Journal Entry")) {
				cur_frm.add_custom_button('Bank Entries', function() {
					frappe.route_options = {
						"Journal Entry Account.reference_type": frm.doc.doctype,
						"Journal Entry Account.reference_name": frm.doc.name,
					};
					frappe.set_route("List", "Journal Entry");
				}, __("View"));
			}
		}
	},
	get_coal_raising_details:function(frm){
		if(frm.doc.branch){
			frappe.call({
				method:'get_coal_raising_details',
				doc:cur_frm.doc,
				callback:function(r){
					cur_frm.refresh_field('items')
					frm.dirty()
				}
			})
		}
	},
});
frappe.ui.form.on('Coal Raising Payment Items',{
	deduction_amount:function(frm, cdt, cdn){
		// let row = locals[cdt][cdn]
		// if (flt(row.deduction_amount) > 0){
		// 	row.total_amount = flt(row.total_amount) - flt(row.deduction_amount)
		// }else{
		// 	row.total_amount = flt(row.total_amount)
		// }
		// cur_frm.refresh_field("items")
		// frm.dirty()
	},
})
