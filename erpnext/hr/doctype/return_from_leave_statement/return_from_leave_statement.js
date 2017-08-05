// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// cur_frm.add_fetch('employee', 'grade', 'grade');
// // cur_frm.add_fetch('employee', 'employee_name_english', 'employee_name_english');
// cur_frm.add_fetch('employee', 'region', 'region');
// cur_frm.add_fetch('employee', 'branch', 'branch');
// cur_frm.add_fetch('employee', 'department', 'department');
// cur_frm.add_fetch('employee', 'designation', 'designation');
cur_frm.add_fetch('leave_application', 'employee_name', 'employee_name');
cur_frm.add_fetch('leave_application','employee','employee');
cur_frm.add_fetch('leave_application', 'total_leave_days', 'total_leave_days');
cur_frm.add_fetch('leave_application', 'leave_approver', 'leave_approver');
cur_frm.add_fetch('leave_application', 'leave_approver_name', 'leave_approver_name');
//cur_frm.add_fetch('leave_application', 'actual_departure_date', 'actual_departure_date');
cur_frm.add_fetch('leave_application', 'from_date', 'from_date');
cur_frm.add_fetch('leave_application', 'to_date', 'to_date');
// cur_frm.add_fetch('leave_application', 'cancel_date', 'cancel_date');
//cur_frm.add_fetch('leave_application', 'actual_departure_date_hijri', 'actual_departure_date_hijri');
// cur_frm.add_fetch('leave_application', 'from_date_hijri', 'from_date_hijri');
// cur_frm.add_fetch('leave_application', 'to_date_hijri', 'to_date_hijri');
// cur_frm.add_fetch('leave_application', 'cancel_date_hijri', 'cancel_date_hijri');

frappe.ui.form.on('Return From Leave Statement', {
	refresh: function(frm) {
		cur_frm.refresh_fields(['employee','leave_application']);
	}
});

cur_frm.fields_dict.leave_application.get_query = function(doc) {
	return{
		filters:[
			/*['employee', '=', doc.employee],*/
			['status', '=', "Approved"],
			['docstatus', '=', 1]
		]
	};
};
cur_frm.cscript.leave_application = function(doc, cdt, cd){
	if (!doc.leave_application) {
		cur_frm.set_value("employee", "");
		cur_frm.set_value("employee_name", "");
		cur_frm.set_value("from_date", "");
		cur_frm.set_value("to_date", "");
		// cur_frm.set_value("from_date_hijri", "");
		// cur_frm.set_value("to_date_hijri", "");
	}
};
// var dates_g = ['return_date'];
// //
// $.each(dates_g, function(index, element) {
//   cur_frm.cscript['custom_' + element] = function(doc, cdt, cd) {
//     cur_frm.set_value(element + '_hijri', doc[element]);
//   };

//   cur_frm.cscript['custom_' + element + '_hijri'] = function(doc, cdt, cd) {
//     cur_frm.set_value(element, doc[element + '_hijri']);
//   };

// });
