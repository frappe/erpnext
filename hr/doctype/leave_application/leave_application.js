// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee','employee_name','employee_name');

cur_frm.cscript.onload = function(doc, dt, dn) {
	if(!doc.posting_date) 
		set_multiple(dt,dn,{posting_date:get_today()});
	if(doc.__islocal) {
		cur_frm.set_value("status", "Open");
		cur_frm.cscript.calculate_total_days(doc, dt, dn);
	}
	
	var leave_approver = doc.leave_approver;
	return cur_frm.call({
		method:"hr.utils.get_leave_approver_list",
		callback: function(r) {
			cur_frm.set_df_property("leave_approver", "options", $.map(r.message, 
				function(profile) { 
					return {value: profile, label: wn.user_info(profile).fullname}; 
				}));
			if(leave_approver) cur_frm.set_value("leave_approver", leave_approver);
			cur_frm.cscript.get_leave_balance(cur_frm.doc);
		}
	});
}

cur_frm.cscript.refresh = function(doc, dt, dn) {
	if(doc.__islocal) {
		cur_frm.set_value("status", "Open")
	}
	cur_frm.set_intro("");
	if(doc.__islocal && !in_list(user_roles, "HR User")) {
		cur_frm.set_intro(wn._("Fill the form and save it"))
	} else {
		if(doc.docstatus==0 && doc.status=="Open") {
			if(user==doc.leave_approver) {
				cur_frm.set_intro(wn._("You are the Leave Approver for this record. Please Update the 'Status' and Save"));
				cur_frm.toggle_enable("status", true);
			} else {
				cur_frm.set_intro(wn._("This Leave Application is pending approval. Only the Leave Apporver can update status."))
				cur_frm.toggle_enable("status", false);
				if(!doc.__islocal) {
						cur_frm.frm_head.appframe.set_title_right("");
				}
			}
		} else {
 			if(doc.status=="Approved") {
				cur_frm.set_intro(wn._("Leave application has been approved."));
				if(cur_frm.doc.docstatus==0) {
					cur_frm.set_intro(wn._("Please submit to update Leave Balance."));
				}
			} else if(doc.status=="Rejected") {
				cur_frm.set_intro(wn._("Leave application has been rejected."));
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
		msgprint(wn._("To Date should be same as From Date for Half Day leave"));
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
			return get_server_fields('get_total_leave_days', '', '', doc, dt, dn, 1);
		}
	}
}

cur_frm.fields_dict.employee.get_query = function() {
	return {
		query: "hr.doctype.leave_application.leave_application.query_for_permitted_employees"
	};
}