// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Specific Gravity', {
	
});
frappe.ui.form.on('Adjust Density', {
	new_specific_gravity: function(frm, cdt, cdn) {
			frappe.call({
				method:"change_quant_on_specific_gravity",
				doc:frm.doc,
				callback: function (r) {
				}
			});
		
	},
	new_quantity: function(frm, cdt, cdn) {
		frappe.call({
			method:"change_spec_grav_on_quant",
			doc: frm.doc,
			callback: function (r) {
				
			}
		});
	
	},
	new_weight: function(frm, cdt, cdn) {
		frappe.call({
			method:"get_specfic_gravity",
			doc: frm.doc,
			callback: function (r) {
				
			}
		});

	},
});
