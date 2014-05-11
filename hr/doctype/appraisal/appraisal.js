// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');

cur_frm.cscript.onload = function(doc,cdt,cdn){
	if(!doc.status) 
		set_multiple(cdt,cdn,{status:'Draft'});
	if(doc.amended_from && doc.__islocal) {
		doc.status = "Draft";
	}
}

cur_frm.cscript.onload_post_render = function(doc,cdt,cdn){
	if(doc.__islocal && doc.employee==wn.defaults.get_user_default("employee")) {
		cur_frm.set_value("employee", "");
		cur_frm.set_value("employee_name", "")
	}
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){

}

cur_frm.cscript.kra_template = function(doc, dt, dn) {
	wn.model.map_current_doc({
		method: "hr.doctype.appraisal.appraisal.fetch_appraisal_template",
		source_name: cur_frm.doc.kra_template,
	});
}

cur_frm.cscript.calculate_total_score = function(doc,cdt,cdn){
	//return get_server_fields('calculate_total','','',doc,cdt,cdn,1);
	var val = getchildren('Appraisal Goal', doc.name, 'appraisal_details', doc.doctype);
	var total =0;
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned)
	}
	doc.total_score = flt(total)
	refresh_field('total_score')
}

cur_frm.cscript.score = function(doc,cdt,cdn){
	var d = locals[cdt][cdn];
	if (d.score){
		if (flt(d.score) > 5) {
			msgprint(wn._("Score must be less than or equal to 5"));
			d.score = 0;
			refresh_field('score', d.name, 'appraisal_details');
		}
		total = flt(d.per_weightage*d.score)/100;
		d.score_earned = total.toPrecision(2);
		refresh_field('score_earned', d.name, 'appraisal_details');
	}
	else{
		d.score_earned = 0;
		refresh_field('score_earned', d.name, 'appraisal_details');
	}
	cur_frm.cscript.calculate_total(doc,cdt,cdn);
}

cur_frm.cscript.calculate_total = function(doc,cdt,cdn){
	var val = getchildren('Appraisal Goal', doc.name, 'appraisal_details', doc.doctype);
	var total =0;
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}
	doc.total_score = flt(total);
	refresh_field('total_score');
}

cur_frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {
	return{	query:"controllers.queries.employee_query" }	
}