// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
	$c_obj(make_doclist(doc.doctype, doc.name), 'fetch_kra', '', 
		function() { 
			cur_frm.refresh();
		});
}

cur_frm.cscript.calculate_total_score = function(doc,cdt,cdn){
	//get_server_fields('calculate_total','','',doc,cdt,cdn,1);
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
			msgprint("Score must be less than or equal to 5");
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

cur_frm.fields_dict.employee.get_query = erpnext.utils.employee_query;