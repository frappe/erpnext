// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

var display_activity_log = function(msg) {
	if(!cur_frm.ss_html)
		cur_frm.ss_html = $a(cur_frm.fields_dict['activity_log'].wrapper,'div');
	cur_frm.ss_html.innerHTML =
		'<div class="padding"><h4>'+__("Activity Log:")+'</h4>'+msg+'</div>';
}

//Create salary slip
//-----------------------
cur_frm.cscript.create_salary_slip = function(doc, cdt, cdn) {
	var callback = function(r, rt){
		if (r.message)
			display_activity_log(r.message);
	}
	return $c('runserverobj', args={'method':'create_sal_slip','docs':doc},callback);
}

cur_frm.cscript.submit_salary_slip = function(doc, cdt, cdn) {
	var check = confirm(__("Do you really want to Submit all Salary Slip for month {0} and year {1}", [doc.month, doc.fiscal_year]));
	if(check){
		var callback = function(r, rt){
			if (r.message)
				display_activity_log(r.message);
		}
		return $c('runserverobj', args={'method':'submit_salary_slip','docs':doc},callback);
	}
}

cur_frm.cscript.make_bank_entry = function(doc,cdt,cdn){
    if(doc.company && doc.month && doc.fiscal_year){
    	cur_frm.cscript.make_jv(doc, cdt, cdn);
    } else {
  	  msgprint(__("Company, Month and Fiscal Year is mandatory"));
    }
}

cur_frm.cscript.make_jv = function(doc, dt, dn) {
	return $c_obj(doc, 'make_journal_entry', '', function(r) {
		var doc = frappe.model.sync(r.message)[0];
		frappe.set_route("Form", doc.doctype, doc.name);
	});
}
