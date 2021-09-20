// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(doc.__islocal) cur_frm.set_value("attendance_date", frappe.datetime.get_today());
	
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date:doc.attendance_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("attendance_date_nepal", resp.message)
				}
			}
		})

}


cur_frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {
	return{
		query: "erpnext.controllers.queries.employee_query"
	}	
	
}

