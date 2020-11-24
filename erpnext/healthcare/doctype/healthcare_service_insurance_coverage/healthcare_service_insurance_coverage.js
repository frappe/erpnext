// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Service Insurance Coverage', {
	refresh: function(frm) {
		frm.set_query('healthcare_insurance_coverage_plan', function(){
				return{
					filters:{
						'is_active': 1
					}
				};
		});
	}
});
