// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

//cur_frm.add_fetch('employee', 'grade', 'grade');
frappe.ui.form.on('Health Insurance Info', {
    employee: function (frm) {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Family Info",
                fields: ["*"],
                filters: {parent: frm.doc.employee}
            },
            callback: function (r) {
                // frm.add_child("family_info", none)
                // console.log(r.message);
                if (r.message) {
                    cur_frm.clear_table("family_info");
                    $.each(r.message, function (i, d) {
                        var row = frappe.model.add_child(cur_frm.doc, "Family Info", "family_info");
                        row.name1 = d.name1;
                        row.gender = d.gender;
                        row.birthdate = d.birthdate;
                        row.passport = d.passport;
                        row.relation = d.relation;
                        row.class = d.class;
                        refresh_field("family_info");
                    });
              
                }
                else {
                    cur_frm.clear_table("family_info");
                    refresh_field("family_info");
                }
               
                
            }
        });
    }
});

cur_frm.add_fetch('employee', 'employee_name', 'employee_name');
//cur_frm.add_fetch('employee', 'employee_name_english', 'employee_name_english');
cur_frm.add_fetch('employee', 'marital_status', 'marital_status');
cur_frm.add_fetch('employee', 'civil_id', 'national_id_number');
//cur_frm.add_fetch('employee', 'id_date_of_issue', 'id_date_of_issue');
cur_frm.add_fetch('employee', 'designation', 'designation');
//cur_frm.add_fetch('employee', 'id_valid_upto', 'id_valid_upto');
cur_frm.add_fetch('employee', 'iban', 'iban');
//cur_frm.add_fetch('employee', 'sponsor', 'sponsor');
cur_frm.add_fetch('employee', 'cell_number', 'cell_number');
cur_frm.add_fetch('employee', 'grade', 'grade');
