// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc, dt, dn) {
	if(!doc.posting_date)
		set_multiple(dt, dn, { posting_date:get_today() });
}

cur_frm.add_fetch('employee','employee_name','employee_name');

cur_frm.cscript.employee = function(doc, dt, dn) {
	calculate_total_leaves_allocated(doc, dt, dn);
}

cur_frm.cscript.leave_type = cur_frm.cscript.period = cur_frm.cscript.carry_forward = cur_frm.cscript.employee;

cur_frm.cscript.carry_forwarded_leaves = function(doc, dt, dn) {
	set_multiple(dt, dn, {total_leaves_allocated : flt(doc.carry_forwarded_leaves) + 
		flt(doc.new_leaves_allocated)});
}

cur_frm.cscript.new_leaves_allocated = cur_frm.cscript.carry_forwarded_leaves;

var calculate_total_leaves_allocated = function(doc, dt, dn) {
	if(cint(doc.carry_forward) == 1 && doc.leave_type && doc.from_period && doc.employee) {
		return cur_frm.call({
			method: "erpnext.hr.doctype.leave_allocation.leave_allocation.get_carry_forwarded_leaves"
		});
	}
	else if(cint(doc.carry_forward) == 0)
		set_multiple(dt, dn, {carry_forwarded_leaves : 0, total_leaves_allocated : flt(doc.new_leaves_allocated)});
}

cur_frm.fields_dict.employee.get_query = function(doc, cdt, cdn) {
	return	{
		query: "erpnext.controllers.queries.employee_query"
	}
}

cur_frm.set_query("from_period", function(doc) {
	if (!doc.period)
		frappe.throw(frappe._("Please select Period first"))
	else if (doc.carry_forward) {
		return	{
			query: "erpnext.hr.doctype.leave_allocation.leave_allocation.from_period_query",
			filters: { "period": doc.period }
		}
	}
});