// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Trip Log', {
	// refresh: function(frm) {

	// }
	onload:function(frm){
		frm.fields_dict['items'].grid.get_field('equipment').get_query = function(){
			return {
				filters: {enabled:1}
			}
		}
	}
});
