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

// On load
//=======================================================================
cur_frm.cscript.onload = function(doc, dt, dn){
  e_tbl = getchildren('Salary Structure Earning', doc.name, 'earning_details', doc.doctype);
  d_tbl = getchildren('Salary Structure Deduction', doc.name, 'deduction_details', doc.doctype);
  if (e_tbl.length == 0 && d_tbl.length == 0)
    $c_obj(make_doclist(doc.doctype,doc.name),'make_earn_ded_table','', function(r, rt) { refresh_many(['earning_details', 'deduction_details']);});
}

// On refresh
//=======================================================================
cur_frm.cscript.refresh = function(doc, dt, dn){
  if((!doc.__islocal) && (doc.is_active == 'Yes')){
    cur_frm.add_custom_button('Make Salary Slip', cur_frm.cscript['Make Salary Slip']);  
  }

  cur_frm.toggle_enable('employee', doc.__islocal);
}


// Make Salry Slip
//=======================================================================
cur_frm.cscript['Make Salary Slip'] = function(){
  var doc = cur_frm.doc;  
  var callback = function(r,rt){
    ret = r.message;
    n = wn.model.make_new_doc_and_get_name("Salary Slip");
    $c('dt_map', args={
      'docs':wn.model.compress([locals["Salary Slip"][n]]),
      'from_doctype':'Salary Structure',
      'to_doctype':'Salary Slip',
      'from_docname':doc.name,
      'from_to_list':"[['Salary Structure', 'Salary Slip'], ['Salary Structure Earning', 'Salary Slip Earning'], ['Salary Structure Deduction', 'Salary Slip Deduction']]"
      }, 
      function(r,rt) {
        n.fiscal_year = sys_defaults.fiscal_year;
        n.bank_name = ret['bank_name'];
        n.bank_account_no = ret['bank_ac_no'];
        n.esic_no=ret['esic_no'];
        n.pf_no= ret['pf_no'];
        loaddoc("Salary Slip", n);
      }
    );
  }
  $c_obj(make_doclist(doc.doctype,doc.name),'get_ss_values',cur_frm.doc.employee, callback); 
}


// get employee details
//=======================================================================
cur_frm.cscript.employee = function(doc, dt, dn){
  if (doc.employee)
    get_server_fields('get_employee_details','','',doc,dt,dn);
}

// calculate earning totals 
//=======================================================================
cur_frm.cscript.modified_value = function(doc, cdt, cdn){
  calculate_totals(doc, cdt, cdn);
}

// calculate deduction totals
//=======================================================================
cur_frm.cscript.d_modified_amt = function(doc, cdt, cdn){
  calculate_totals(doc, cdt, cdn);
}

// calculate totals
//=======================================================================
var calculate_totals = function(doc, cdt, cdn) {
  var tbl1 = getchildren('Salary Structure Earning', doc.name, 'earning_details', doc.doctype);
  var tbl2 = getchildren('Salary Structure Deduction', doc.name, 'deduction_details', doc.doctype);
  
  var total_earn = 0; var total_ded = 0;
  for(var i = 0; i < tbl1.length; i++){
    total_earn += flt(tbl1[i].modified_value);
  }
  for(var j = 0; j < tbl2.length; j++){
    total_ded += flt(tbl2[j].d_modified_amt);
  }
  doc.total_earning = total_earn;
  doc.total_deduction = total_ded;
  doc.net_pay = flt(total_earn) - flt(total_ded);
  refresh_many(['total_earning', 'total_deduction', 'net_pay']);
}

// validate
//=======================================================================
cur_frm.cscript.validate = function(doc, cdt, cdn) {
  calculate_totals(doc, cdt, cdn);
}

cur_frm.fields_dict.employee.get_query = erpnext.utils.employee_query;