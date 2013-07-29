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

// ****************************************** onload ********************************************************
cur_frm.cscript.onload = function(doc, dt, dn) {
  if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});
}


// ************************************** client triggers ***************************************************
// ---------
// employee
// ---------
cur_frm.add_fetch('employee','employee_name','employee_name');

cur_frm.cscript.employee = function(doc, dt, dn) {
  calculate_total_leaves_allocated(doc, dt, dn);
}

// -----------
// leave type
// -----------
cur_frm.cscript.leave_type = function(doc, dt, dn) {
  calculate_total_leaves_allocated(doc, dt, dn);
}

// ------------
// fiscal year
// ------------
cur_frm.cscript.fiscal_year = function(doc, dt, dn) {
  calculate_total_leaves_allocated(doc, dt, dn);
}

// -------------------------------
// include previous leave balance
// -------------------------------
cur_frm.cscript.carry_forward = function(doc, dt, dn) {
  calculate_total_leaves_allocated(doc, dt, dn);
}

// -----------------------
// previous balance leaves
// -----------------------
cur_frm.cscript.carry_forwarded_leaves = function(doc, dt, dn) {
  set_multiple(dt,dn,{total_leaves_allocated : flt(doc.carry_forwarded_leaves)+flt(doc.new_leaves_allocated)});
}

// ---------------------
// new leaves allocated
// ---------------------
cur_frm.cscript.new_leaves_allocated = function(doc, dt, dn) {
  set_multiple(dt,dn,{total_leaves_allocated : flt(doc.carry_forwarded_leaves)+flt(doc.new_leaves_allocated)});
}


// ****************************************** utilities ******************************************************
// ---------------------------------
// calculate total leaves allocated
// ---------------------------------
calculate_total_leaves_allocated = function(doc, dt, dn) {
  if(cint(doc.carry_forward) == 1 && doc.leave_type && doc.fiscal_year && doc.employee){
    return get_server_fields('get_carry_forwarded_leaves','','', doc, dt, dn, 1);
	}
  else if(cint(doc.carry_forward) == 0){
    set_multiple(dt,dn,{carry_forwarded_leaves : 0,total_leaves_allocated : flt(doc.new_leaves_allocated)});
  }
}

cur_frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {
  return{
    query:"controllers.queries.employee_query"
  } 
}