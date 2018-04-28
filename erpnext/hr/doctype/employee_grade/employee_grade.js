// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee', 'grade', 'grade');
cur_frm.add_fetch('grade', 'insurance', 'insurance');

frappe.ui.form.on('Employee Grade', {
  refresh: function(frm) {
		frm.trigger("toggle_fields");
		frm.fields_dict['earnings'].grid.set_column_disp("default_amount", false);
		frm.fields_dict['deductions'].grid.set_column_disp("default_amount", false);
  },
  	onload: function(frm) {
		if ((cint(frm.doc.__islocal) !== 1)) {
			frm.set_df_property("accomodation_percentage", "read_only", frm.doc.accommodation_from_company);
			frm.set_df_property("accommodation_value", "read_only", frm.doc.accommodation_from_company);
		 }
		 
		frm.set_query("salary_component", "earnings", function() {
			return {
				filters: {
					type: "earning"
				}
			}
		});
		
		frm.set_query("salary_component", "deductions", function() {
			return {
				filters: {
					type: "deduction"
				}
			}
		});
	},
	toggle_fields: function(frm) {
		frm.toggle_display(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
		frm.toggle_reqd(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet);
	}
	//~ ,
	//~ level_value : function(frm) {
		//~ if (frm.doc.base >0)
		//~ {
			//~ frm.set_value("level_percent",frm.doc.level_value*frm.doc.base/100)
		//~ }
	//~ }
	//~ ,
	//~ level_percent : function(frm) {
		//~ if (frm.doc.base >0)
		//~ {
			//~ frm.set_value("level_value",frm.doc.level_percent*frm.doc.base/100)
		//~ }
	//~ }
});


cur_frm.cscript.custom_level_value = function(doc, dt, dn) {
	if (doc.base >0)
	{
		cur_frm.set_value("level_percent",doc.level_value*100/doc.base)
	}

};
cur_frm.cscript.custom_level_percent = function(doc, dt, dn) {
	if (doc.base >0)
	{
		cur_frm.set_value("level_value",doc.level_percent*doc.base/100)
	}

};
