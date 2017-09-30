// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch('leave_application', 'employee', 'employee');
cur_frm.add_fetch('leave_application', 'employee_name', 'employee_name');
cur_frm.add_fetch('leave_application', 'from_date', 'from_date');
cur_frm.add_fetch('leave_application', 'to_date', 'to_date');


frappe.ui.form.on('Cancel Leave Application', {




    refresh: function(frm) {
        // frm.add_custom_button(__("Cancel Leave Application"), function() {
        //     // When this button is clicked, do this

        //     var leave_app = frm.doc.leave_application;
        //     frappe.call({
        //         method: "cancel_leave_app",
        //         args: {
        //             "leave_app": leave_app,
        //         },
        //         doc: cur_frm.doc, // this line is required

        //         callback: function(r) {

        //             alert("" + r.message)
        //         }
        //     });

        // });

        if (!cur_frm.doc.__islocal) {
            for (var key in cur_frm.fields_dict) {
                cur_frm.fields_dict[key].df.read_only = 1;
            }
            cur_frm.disable_save();
        } else {
            cur_frm.enable_save();
        }
    }
});

cur_frm.cscript.leave_application = function(doc, cdt, cd) {
    if (!doc.leave_application) {
        cur_frm.set_value("employee", "");
        cur_frm.set_value("employee_name", "");
        cur_frm.set_value("from_date", "");
        cur_frm.set_value("to_date", "");

        cur_frm.set_value("cancel_date", "");
    }
};

cur_frm.fields_dict.leave_application.get_query = function(doc) {
    return {
        filters: [
            ['is_canceled', '!=', 1],
            ['docstatus', '!=', 2],
        ]
    };
};
cur_frm.add_fetch('leave_application', 'department', 'department');