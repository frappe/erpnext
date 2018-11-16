// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'company', 'company');

frappe.ui.form.on('Attendance Request', {
	half_day: function(frm) {
		if(frm.doc.half_day == 1){
			frm.set_df_property('half_day_date', 'reqd', true);
		}
		else{
			frm.set_df_property('half_day_date', 'reqd', false);
		}
	}
});
