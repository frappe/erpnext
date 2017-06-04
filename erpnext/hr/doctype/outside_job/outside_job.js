// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("employee", "employee_name", "employee_name");

frappe.ui.form.on('Outside Job', {
	refresh: function(frm) {
		cur_frm.cscript.type(cur_frm.doc);
		frm.set_query("employee", erpnext.queries.employee);
		frm.set_query("reports_to", function() {
			return {
				query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				filters: {
					employee: frm.doc.employee
				}
			};
		});
	}
});



cur_frm.cscript.type = function(doc, cdt, cd){

	daily = 'Daily';
	hourly = 'Hourly';
	if( doc.type == hourly ){

		toggle_hourly_section(true);
		toggle_daily_section(false);


	}else if( doc.type == daily ){
		toggle_hourly_section(false);
		toggle_daily_section(true);

	}
};
cur_frm.cscript.employee = function(doc, cdt, cd){
	if (!doc.employee) {
		cur_frm.set_value("employee_name", "");
	}
};


function toggle_hourly_section(show) {

	cur_frm.toggle_display('hourly_section_break', show);

	cur_frm.toggle_reqd('hourly_date', show);
	cur_frm.toggle_reqd('hourly_hour_count', show);
}


function toggle_daily_section(show) {
	// alert('daily_section_break:'+show)
	cur_frm.toggle_display('daily_section_break', show);

	cur_frm.toggle_reqd('daily_from_date', show);
	cur_frm.toggle_reqd('daily_to_date', show);
}

var numbers_only_fields = ["hourly_hour_count"];

$.each(numbers_only_fields, function(index, value) {
  $('[data-fieldname=' + value + ']').on('keypress', numbersonly);
});

function numbersonly(e) {
  var unicode = e.charCode ? e.charCode : e.keyCode;
    if (unicode != 8) { //if the key isn't the backspace key (which we should allow)
      if (unicode < 46 || unicode > 57) //if not a number
        return false; //disable key press
    }
}


