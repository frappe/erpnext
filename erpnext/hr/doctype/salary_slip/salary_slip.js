// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'company', 'company');

cur_frm.cscript.onload = function(doc, dt, dn) {
	if((cint(doc.__islocal) == 1) && !doc.amended_from) {
		if(!doc.month) {
			var today = new Date();
			month = (today.getMonth() + 01).toString();
			if(month.length > 1) doc.month = month;
			else doc.month = '0' + month;
		}
		refresh_field('month');
		cur_frm.cscript.month();
	}
}

// Get leave details
cur_frm.cscript.employee = function(doc, dt, dn) {
	return $c_obj(make_doclist(doc.doctype, doc.name), 'get_emp_and_leave_details', '', function(r, rt) {
		var doc = locals[dt][dn];
		cur_frm.refresh();
		calculate_all(doc, dt, dn);
	});
}

cur_frm.cscript.month = cur_frm.cscript.employee;

cur_frm.cscript.leave_without_pay = function(doc, dt, dn) {
	if (doc.employee && doc.month) {
		return $c_obj(make_doclist(doc.doctype, doc.name), 'get_leave_details', doc.leave_without_pay, function(r, rt) {
			var doc = locals[dt][dn];
			cur_frm.refresh();
			calculate_all(doc, dt, dn);
		});
	}
}

var calculate_all = function(doc, dt, dn) {
	calculate_earning_total(doc, dt, dn);
	calculate_ded_total(doc, dt, dn);
	calculate_net_pay(doc, dt, dn);
}

cur_frm.cscript.e_modified_amount = function(doc, dt, dn) {
	calculate_earning_total(doc, dt, dn);
	calculate_net_pay(doc, dt, dn);
}

cur_frm.cscript.e_depends_on_lwp = cur_frm.cscript.e_modified_amount;

// Trigger on earning modified amount and depends on lwp
cur_frm.cscript.d_modified_amount = function(doc, dt, dn) {
	calculate_ded_total(doc, dt, dn);
	calculate_net_pay(doc, dt, dn);
}

cur_frm.cscript.d_depends_on_lwp = cur_frm.cscript.d_modified_amount;

var calculate_earning_total = function(doc, dt, dn) {
	var tbl = getchildren('Salary Slip Earning', doc.name, 'earning_details', doc.doctype);

	var total_earn = 0;
	for(var i = 0; i < tbl.length; i++) {
		if(cint(tbl[i].e_depends_on_lwp) == 1) {
			tbl[i].e_modified_amount = 
				Math.round(tbl[i].e_amount) * (flt(doc.payment_days) / cint(doc.total_days_in_month) * 100) / 100;			
			refresh_field('e_modified_amount', tbl[i].name, 'earning_details');
		}
		total_earn += flt(tbl[i].e_modified_amount);
	}
	doc.gross_pay = total_earn + flt(doc.arrear_amount) + flt(doc.leave_encashment_amount);
	refresh_many(['e_modified_amount', 'gross_pay']);
}

var calculate_ded_total = function(doc, dt, dn) {
	var tbl = getchildren('Salary Slip Deduction', doc.name, 'deduction_details', doc.doctype);

	var total_ded = 0;
	for(var i = 0; i < tbl.length; i++) {
		if(cint(tbl[i].d_depends_on_lwp) == 1) {
			tbl[i].d_modified_amount = 
				Math.round(tbl[i].d_amount) * (flt(doc.payment_days) / cint(doc.total_days_in_month) * 100) / 100;
			refresh_field('d_modified_amount', tbl[i].name, 'deduction_details');
		}
		total_ded += flt(tbl[i].d_modified_amount);
	}
	doc.total_deduction = total_ded;
	refresh_field('total_deduction');	
}

var calculate_net_pay = function(doc, dt, dn) {
	doc.net_pay = flt(doc.gross_pay) - flt(doc.total_deduction);
	doc.rounded_total = Math.round(doc.net_pay);
	refresh_many(['net_pay', 'rounded_total']);
}

cur_frm.cscript.arrear_amount = function(doc, dt, dn) {
	calculate_earning_total(doc, dt, dn);
	calculate_net_pay(doc, dt, dn);
}

cur_frm.cscript.leave_encashment_amount = cur_frm.cscript.arrear_amount;

cur_frm.cscript.validate = function(doc, dt, dn) {
	calculate_all(doc, dt, dn);
}

cur_frm.cscript.month = function(doc, dt, dn) {
	if (cur_frm.doc.month) {
		cur_frm.set_value("from_date", wn.datetime.month_start(null, cur_frm.doc.month));
		cur_frm.set_value("to_date", wn.datetime.month_end(null, cur_frm.doc.month));
	}
}

cur_frm.fields_dict.employee.get_query = function(doc, cdt, cdn) {
	return {
		query: "erpnext.controllers.queries.employee_query"
	}		
}