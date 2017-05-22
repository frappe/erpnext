// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("employee", "employee_name", "employee_name");

frappe.ui.form.on('Job Assignment Report', {
  refresh: function(frm) {

  }
});

cur_frm.fields_dict.job_assignment.get_query = function(doc) {
  return {
    filters: [
      ['employee', '=', doc.employee]
    ]
  };
};

cur_frm.cscript.custom_employee = function(doc, cdt, cd) {
  doc.job_assignment = "";
	cur_frm.add_fetch("employee", "employee_name", "employee_name");
  cur_frm.refresh_fields(['job_assignment','employee']);
};
