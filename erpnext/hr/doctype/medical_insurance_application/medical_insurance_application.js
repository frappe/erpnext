// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee','department','department');
frappe.ui.form.on('Medical Insurance Application', {
    onload: function(frm){
        
    },refresh: function(frm) {
        if (!cur_frm.doc.__islocal) {
        	for (var key in cur_frm.fields_dict) {
            cur_frm.fields_dict[key].df.read_only = 1;
            }
        }
        else{
        	cur_frm.enable_save();
        }


    },
    get_medical_disclaimer_templete: function(frm){
        // window.location.href = repl(frappe.request.url +
        //     '?cmd=%(cmd)s&from_date=%(from_date)s&to_date=%(to_date)s', {
        //         cmd: "erpnext.hr.doctype.medical_insurance_application.medical_insurance_application.get_template"
        //     });
        window.open("assets/Medical_Declaration_Form_V1.2016.pdf");
    },
	employee: function (frm) {
        if(frm.doc.nationality == "Saudi" || frm.doc.nationality == "Saudi Arabia"){
            // alert("fgg");
            cur_frm.fields_dict["attachments"].df.reqd = 1
        }
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
