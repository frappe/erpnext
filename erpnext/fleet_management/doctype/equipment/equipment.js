// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Equipment', {
	refresh: function(frm) {

	},
	equipment_category:function(frm){
		frm.set_query('equipment_type', function(doc) {
			return {
				filters: {
					"disabled": 0,
					"equipment_category": doc.equipment_category
				}
			};
		});
	},
	equipment_type:function(frm){
		frm.set_query('equipment_model', function(doc) {
			return {
				filters: {
					"disabled": 0,
					"equipment_type": doc.equipment_type
				}
			};
		});
	}
});
