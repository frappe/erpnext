// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Equipment Modifier Tool', {
	// refresh: function(frm) {

	// }
	new_equipment_category:function(frm){
		frm.set_query('new_equipment_type', function(doc) {
			return {
				filters: {
					"disabled": 0,
					"equipment_category": doc.new_equipment_category
				}
			};
		});
	},
	new_equipment_type:function(frm){
		frm.set_query('new_equipment_model', function(doc) {
			return {
				filters: {
					"disabled": 0,
					"equipment_type": doc.new_equipment_type
				}
			};
		});
	}
});
