// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("employee", "employee_name", "employee_name");
cur_frm.add_fetch('employee', 'department', 'department');
frappe.ui.form.on('Employee Resignation', {
    refresh: function(frm) {
        if (!cur_frm.doc.__islocal) {
        	for (var key in cur_frm.fields_dict){
        		cur_frm.fields_dict[key].df.read_only =1; 
        	}
            cur_frm.disable_save();
        }
        else{
        	cur_frm.enable_save();
        }


    }
});
