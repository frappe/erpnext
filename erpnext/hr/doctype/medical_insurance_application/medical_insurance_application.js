// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Medical Insurance Application', {
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
                    cur_frm.clear_table("family_members");
                    $.each(r.message, function (i, d) {
                        var row = frappe.model.add_child(cur_frm.doc, "Family Info", "family_members");
                        row.name1 = d.name1;
                        row.gender = d.gender;
                        row.birthdate = d.birthdate;
                        row.passport = d.passport;
                        row.relation = d.relation;
                        row.class = d.class;
                        refresh_field("family_members");
                    });
              
                }
                else {
                    cur_frm.clear_table("family_members");
                    refresh_field("family_members");
                }
               
                
            }
        });
    }
});
