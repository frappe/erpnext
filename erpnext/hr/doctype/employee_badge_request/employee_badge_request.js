// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'grade', 'grade');
// cur_frm.add_fetch('employee', 'employee_name', 'employee_name');
// cur_frm.add_fetch('employee', 'employee_name_english', 'employee_name_english');
// cur_frm.add_fetch('employee', 'region', 'region');
cur_frm.add_fetch('employee', 'branch', 'branch');
cur_frm.add_fetch('employee', 'department', 'department');
cur_frm.add_fetch('employee', 'designation', 'designation');
cur_frm.add_fetch('employee', 'employment_type', 'employment_type');
// cur_frm.add_fetch('employee', 'civil_identity_number', 'civil_identity_number');
cur_frm.add_fetch('employee', 'date_of_joining', 'date_of_joining');
cur_frm.add_fetch('employee', 'nationality', 'nationality');
cur_frm.add_fetch('employee', 'gender', 'gender');

frappe.ui.form.on('Employee Badge Request', {
  refresh: function(frm) {
		if (frm.doc.__islocal) {
			// get_employee_illnes(frm.doc);
		}
  }
});
var dates_g = ['date'];

$.each(dates_g, function(index, element) {
  cur_frm.cscript['custom_' + element] = function(doc, cdt, cd) {
    cur_frm.set_value(element + '_hijri', doc[element]);
  };

  cur_frm.cscript['custom_' + element + '_hijri'] = function(doc, cdt, cd) {
    cur_frm.set_value(element, doc[element + '_hijri']);
  };

});

cur_frm.cscript.custom_employee = function(doc, cdt, cd) {
// get_employee_illnes(doc);
};

get_employee_illnes = function(doc) {
  if (doc.employee) {
    frappe.call({
      method: 'get_employee_illnes',
      doc: doc,
      callback: function(e) {
				console.log(e.message);
				cur_frm.refresh_fields(["special_case"]);
			}
    });
  }
};
