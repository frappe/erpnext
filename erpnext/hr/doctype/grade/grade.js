// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Grade', {
  refresh: function(frm) {
		frm.trigger("toggle_fields");
		frm.fields_dict['earnings'].grid.set_column_disp("default_amount", false);
		frm.fields_dict['deductions'].grid.set_column_disp("default_amount", false);
  },
  	onload: function(frm) {
		
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
});
$('[data-fieldname="main_earning"]').on('keypress', numbersonly);
$('[data-fieldname="accommodation"]').on('keypress', numbersonly);


function numbersonly(e) {
  var unicode = e.charCode ? e.charCode : e.keyCode;
  if (unicode != 8) { //if the key isn't the backspace key (which we should allow)
    if (unicode < 48 || unicode > 57) //if not a number
      return false; //disable key press
  }
}

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee', 'grade', 'grade');
cur_frm.add_fetch('grade', 'insurance', 'insurance');

cur_frm.cscript.onload = function(doc, dt, dn) {
  if ((cint(doc.__islocal) !== 1)) {
    cur_frm.set_df_property("accomodation_percentage", "read_only", doc.accommodation_from_company);
    cur_frm.set_df_property("accommodation_value", "read_only", doc.accommodation_from_company);
  }
};

cur_frm.cscript.refresh = function(doc, dt, dn) {

};


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
