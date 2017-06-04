// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('leave_application','employee','employee');
cur_frm.add_fetch('leave_application','employee_name','employee_name');
cur_frm.add_fetch('leave_application','from_date','from_date');
cur_frm.add_fetch('leave_application','to_date','to_date');
cur_frm.add_fetch('leave_application','leave_approver','leave_approver');
cur_frm.add_fetch('leave_application','leave_approver_name','leave_approver_name');


frappe.ui.form.on('Return or Cancel Leave Application', {
	refresh: function(frm) {

	}
});

cur_frm.cscript.leave_application = function(doc, cdt, cd){
	if (!doc.leave_application) {
		cur_frm.set_value("employee", "");
		cur_frm.set_value("employee_name", "");
		cur_frm.set_value("from_date", "");
		cur_frm.set_value("to_date", "");
		cur_frm.set_value("cancel_date", "");
	}
};

cur_frm.fields_dict.leave_application.get_query = function(doc) {
	return{
		filters:[
			['is_canceled', '=', 0],
			['half_day', '=', 0],
			['docstatus', '=', 1],
		]
	};
};
