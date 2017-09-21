// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee','department','department');

frappe.ui.form.on('Overtime Request', {
    refresh: function(frm) {
        if (!cur_frm.doc.__islocal) {
        	for (var key in cur_frm.fields_dict){
        		cur_frm.fields_dict[key].df.read_only =1; 
        	}
            cur_frm.disable_save();
        } else {
            cur_frm.enable_save();
        }


    },
    from_date: function(frm) {
        if (frm.doc.to_date) {
            frm.trigger("get_overtime_records");
        }
    },
    to_date: function(frm) {
        frm.trigger("get_overtime_records");
    },
    get_overtime_records: function() {
        frappe.call({
            method: "get_overtime_records",
            doc: cur_frm.doc,
            callback: function(r) {
                // console.log(r.message);
                cur_frm.refresh();
            }
        });
    }
});
cur_frm.cscript.custom_hours = function(doc, cdt, cdn) {
    var d = locals[cdt][cdn];

    frappe.call({
        method: "erpnext.hr.doctype.leave_application.leave_application.get_holidays",
        args: {
            "employee": cur_frm.doc.employee,
            "from_date": d.date,
            "to_date": d.date
        },
        callback: function(r) {
            if (r.message >= 1) {
                if (d.hours > 6) {
                    frappe.throw(__("You can't insert more than 6 hours as overtime in a holiday day"));
                }
            } else {
                if (d.hours > 3) {
                    frappe.throw(__("You can't insert more than 3 hours as overtime in a working day"));
                }
            }

        }
    });
    var val = 0
    $.each((doc.overtime_details), function(i, d) {
        val += d.hours;
    });
    cur_frm.set_value("total_hours", val);
    cur_frm.set_value("total_modified_hours", val * 1.5);
    // console.log(val);
}
// function get_overtime_records(){
// 	alert("Dfd");
//         frappe.call({
//             method: "get_overtime_records",
//             args: {
//                 doc: cur_frm.doc
//             },
//             callback: function(r) {
//                 console.log(r.message);
//                 cur_frm.refresh();
//             }
//         });
// };
frappe.ui.form.on('Overtime Detail', {
    //  overtime_details_add: function(frm) {
    //    // adding a row ... or on btn add row
    // },
    overtime_details_remove: function(frm) {
        cur_frm.refresh();
        // removing a row ... or on btn delete 
    }
});