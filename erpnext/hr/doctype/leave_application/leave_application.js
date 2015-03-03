// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee','employee_name','employee_name');

cur_frm.cscript.onload = function(doc, dt, dn) {
	if(!doc.posting_date)
		set_multiple(dt,dn,{posting_date:get_today()});
	if(doc.__islocal) {
		cur_frm.set_value("status", "Open");
		cur_frm.cscript.calculate_total_days(doc, dt, dn);
	}

	cur_frm.set_query("leave_approver", function() {
		return {
			filters: [["UserRole", "role", "=", "Leave Approver"]]
		};
	});

	cur_frm.cscript.get_leave_balance(cur_frm.doc);
}

cur_frm.cscript.refresh = function(doc, dt, dn) {
	if(doc.__islocal) {
		cur_frm.set_value("status", "Open")
	}
	cur_frm.set_intro("");
	if(doc.__islocal && !in_list(user_roles, "HR User")) {
		cur_frm.set_intro(__("Fill the form and save it"))
	} else {
		if(doc.docstatus==0 && doc.status=="Open") {
			if(user==doc.leave_approver) {
				cur_frm.set_intro(__("You are the Leave Approver for this record. Please Update the 'Status' and Save"));
				cur_frm.toggle_enable("status", true);
			} else {
				cur_frm.set_intro(__("This Leave Application is pending approval. Only the Leave Approver can update status."))
				cur_frm.toggle_enable("status", false);
			}
		}
	}
}

cur_frm.cscript.employee = function (doc, dt, dn){
	cur_frm.cscript.get_leave_balance(doc, dt, dn);
}

cur_frm.cscript.fiscal_year = function (doc, dt, dn){
	cur_frm.cscript.get_leave_balance(doc, dt, dn);
}

cur_frm.cscript.leave_type = function (doc, dt, dn){
	cur_frm.cscript.get_leave_balance(doc, dt, dn);
}

cur_frm.cscript.half_day = function(doc, dt, dn) {
	if(doc.from_date) {
		set_multiple(dt,dn,{to_date:doc.from_date});
		cur_frm.cscript.calculate_total_days(doc, dt, dn);
	}
}

cur_frm.cscript.from_date = function(doc, dt, dn) {
	if(cint(doc.half_day) == 1){
		set_multiple(dt,dn,{to_date:doc.from_date});
	}
	cur_frm.cscript.calculate_total_days(doc, dt, dn);
}

cur_frm.cscript.to_date = function(doc, dt, dn) {
	if(cint(doc.half_day) == 1 && cstr(doc.from_date) && doc.from_date != doc.to_date){
		msgprint(__("To Date should be same as From Date for Half Day leave"));
		set_multiple(dt,dn,{to_date:doc.from_date});
	}
	cur_frm.cscript.calculate_total_days(doc, dt, dn);
}

cur_frm.cscript.get_leave_balance = function(doc, dt, dn) {
	if(doc.docstatus==0 && doc.employee && doc.leave_type && doc.fiscal_year) {
		return cur_frm.call({
			method: "get_leave_balance",
			args: {
				employee: doc.employee,
				fiscal_year: doc.fiscal_year,
				leave_type: doc.leave_type
			}
		});
	}
}

cur_frm.cscript.calculate_total_days = function(doc, dt, dn) {
	if(doc.from_date && doc.to_date){
		if(cint(doc.half_day) == 1) set_multiple(dt,dn,{total_leave_days:0.5});
		else{
			// server call is done to include holidays in leave days calculations
			return frappe.call({
				method: 'erpnext.hr.doctype.leave_application.leave_application.get_total_leave_days',
				args: {leave_app: doc},
				callback: function(response) {
					if (response && response.message) {
						cur_frm.set_value('total_leave_days', response.message.total_leave_days);
					}
				}
			});
		}
	}
}

cur_frm.fields_dict.employee.get_query = erpnext.queries.employee;

frappe.ui.form.on("Leave Application", "leave_approver", function(frm) {
	frappe.call({
		"method": "frappe.client.get",
		args: {
			doctype: "User",
			name: frm.doc.leave_approver
		},
		callback: function (data) {
			frappe.model.set_value(frm.doctype, frm.docname, "leave_approver_name",
				data.message.first_name
				+ (data.message.last_name ? (" " + data.message.last_name) : ""))
		}
	})
})
