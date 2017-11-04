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
cur_frm.add_fetch('employee', 'department', 'department');
frappe.ui.form.on('Employee Badge Request', {
    refresh: function(frm) {

        // if (!cur_frm.doc.__islocal) {
        // 	for (var key in cur_frm.fields_dict){
        //         cur_frm.fields_dict[key].df.read_only =1; 
        //     }
        //     cur_frm.disable_save();
        // }
        // else{
        //     if (roles.indexOf("HR Specialist")!= -1){
        //         cur_frm.fields_dict["badge_received"].df.read_only=0;
        //         cur_frm.refresh_fields(["badge_received"]);

        //     }
        // 	cur_frm.enable_save();
        // }
    },
    validate: function(frm) {
        // if (!frm.doc.__islocal) {
        //     if (frm.doc.badge_received != "Yes") {
        //         frappe.throw(__("Employee must recieve the Badge before submit"));
        //     }
        // }
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
