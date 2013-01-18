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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

cur_frm.cscript.onload = function(doc) {
	// bc
	var india_specific = ["esic_card_no", "gratuity_lic_id", "pan_number", "pf_number"]
	if(wn.control_panel.country!="India") {
		hide_field(india_specific);
	}
}

cur_frm.cscript.refresh = function(doc) {
	if(!doc.__islocal) {
		hide_field("naming_series");
		cur_frm.add_custom_button('Make Salary Structure', 
			cur_frm.cscript['Make Salary Structure']);
	}
}

cur_frm.cscript.date_of_birth = function(doc, dt, dn) {
	get_server_fields('get_retirement_date','','',doc,dt,dn,1);
}

cur_frm.cscript.salutation = function(doc,dt,dn) {
	if(doc.salutation){
		if(doc.salutation=='Mr')
			doc.gender='Male';
		else if(doc.salutation=='Ms')
			doc.gender='Female';
		refresh_field('gender');
	}
}

cur_frm.cscript['Make Salary Structure']=function(){
	$c_obj(make_doclist (cur_frm.doc.doctype, cur_frm.doc.name), 'check_sal_structure',
	 	cur_frm.doc.name, function(r, rt) {
			if(r.message)
				msgprint("You have already created Active salary structure.\n \
					If you want to create new one, please ensure that no active salary structure \
					 exist.\nTo inactive salary structure select 'Is Active' as 'No'.");
			else
				cur_frm.cscript.make_salary_structure(cur_frm.doc); 
		}
	);
}

cur_frm.cscript.make_salary_structure = function(doc, dt, dn, det){
	var st = wn.model.make_new_doc_and_get_name('Salary Structure');
	st = locals['Salary Structure'][st];
	st.employee = doc.name;
	st.employee_name = doc.employee_name;
	st.branch=doc.branch;
	st.designation=doc.designation;
	st.department=doc.department;
	st.fiscal_year = doc.fiscal_year
	st.grade=doc.grade;
	loaddoc('Salary Structure', st.name);
}

cur_frm.fields_dict.user_id.get_query = erpnext.utils.profile_query;

cur_frm.fields_dict.reports_to.get_query = erpnext.utils.employee_query;