// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee','department','department');

frappe.ui.form.on('Overtime Request', {
    refresh: function(frm) {
        // if (!cur_frm.doc.__islocal) {
        // 	for (var key in cur_frm.fields_dict){
        // 		cur_frm.fields_dict[key].df.read_only =1; 
        // 	}
        //     cur_frm.disable_save();
        // } else {
        //     cur_frm.enable_save();
        // }


    },
    workflow_state: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
    },
    validate: function(frm){

        cur_frm.refresh_fields(["workflow_state"]);
        // if (cur_frm.doc.workflow_state.indexOf("Approve") !== -1 || cur_frm.doc.workflow_state.indexOf("Reject") !== -1){
        //     if(cur_frm.doc.to_date >= frappe.datetime.nowdate()){
        //         cur_frm.doc.workflow_state = "Pending";
        //         frappe.throw(__("You can't Approve or Reject before month end"));
        //     }
        // }
    },
    month: function(frm){
    	if (frm.doc.month){

    		var month_arr=new Array(12);
				month_arr["January"]=0;
				month_arr["February"]=1;
				month_arr["March"]=2;
				month_arr["April"]=3;
				month_arr["May"]=4;
				month_arr["June"]=5;
				month_arr["July"]=6;
				month_arr["August"]=7;
				month_arr["September"]=8;
				month_arr["October"]=9;
				month_arr["November"]=10;
				month_arr["December"]=11;

    		var date = new Date();
    		var month = frm.doc.month;

    		date.setMonth(month_arr[month])
    		date.setDate(1)
			var firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
			var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
			var first_day_exp =firstDay.getFullYear()+'-' + (firstDay.getMonth()+1) + '-'+firstDay.getDate();//prints expected format.
			var last_day_exp =lastDay.getFullYear()+'-' + (lastDay.getMonth()+1) + '-'+lastDay.getDate();//prints expected format.

    		frm.doc.from_date = first_day_exp;
    		frm.doc.to_date=last_day_exp;

    		cur_frm.refresh();
    		if (frm.doc.month) {
            	frm.trigger("get_overtime_records");
            }



    	}
    }
    ,
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
// frappe.ui.form.on('Supplier Quotation Item', {
//     //  overtime_details_add: function(frm) {
//     //    // adding a row ... or on btn add row
//     // },
//     quotations_add: function(frm) {
//       alert("dgfg");
//         // removing a row ... or on btn delete 
//     }
// });