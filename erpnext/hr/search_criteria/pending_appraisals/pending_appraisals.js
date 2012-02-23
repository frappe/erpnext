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

report.customize_filters = function() {
  this.hide_all_filters();  
  
  this.add_filter({fieldname:'approver', label:'Approver', fieldtype:'Link', options:'Profile', ignore : 1, parent:'Appraisal'});  
  this.filter_fields_dict['Appraisal'+FILTER_SEP +'Approver'].df.in_first_page = 1;
  
  this.filter_fields_dict['Appraisal'+FILTER_SEP +'Employee'].df.filter_hide = 0;
  this.filter_fields_dict['Appraisal'+FILTER_SEP +'Employee Name'].df.filter_hide = 0;
  this.filter_fields_dict['Appraisal'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;  
  this.filter_fields_dict['Appraisal'+FILTER_SEP +'From Start Date'].df.filter_hide = 0;
  //this.filter_fields_dict['Appraisal'+FILTER_SEP +'To Start Date'].df.filter_hide = 0;
  //this.filter_fields_dict['Appraisal'+FILTER_SEP +'From End Date'].df.filter_hide = 0;
  this.filter_fields_dict['Appraisal'+FILTER_SEP +'To End Date'].df.filter_hide = 0;
}
this.mytabs.items['Select Columns'].hide();

report.get_query = function(){
  //get filter values
  emp = this.filter_fields_dict['Appraisal'+FILTER_SEP+'Employee'].get_value(); 
  emp_nm = this.filter_fields_dict['Appraisal'+FILTER_SEP+'Employee Name'].get_value(); 
  frm_start_date = this.filter_fields_dict['Appraisal'+FILTER_SEP+'From Start Date'].get_value(); 
  //to_start_date = this.filter_fields_dict['Appraisal'+FILTER_SEP+'To Start Date'].get_value(); 
  //frm_end_date = this.filter_fields_dict['Appraisal'+FILTER_SEP+'From End Date'].get_value(); 
  to_end_date = this.filter_fields_dict['Appraisal'+FILTER_SEP+'To End Date'].get_value(); 
  fiscal_year = this.filter_fields_dict['Appraisal'+FILTER_SEP+'Fiscal Year'].get_value();
  approver = this.filter_fields_dict['Appraisal'+FILTER_SEP+'Approver'].get_value();
  
  var cond = '';
  if(emp) cond += ' AND `tabAppraisal`.employee = "'+emp+'"';
  if(emp_nm) cond += ' AND `tabAppraisal`.employee_name = "'+emp_nm+'"';
  if(frm_start_date) cond += ' AND `tabAppraisal`.start_date >= "'+frm_start_date+'"';
  //if(to_start_date) cond += ' AND `tabAppraisal`.start_date <= "'+to_start_date+'"';
  //if(frm_end_date) cond += ' AND `tabAppraisal`.end_date >= "'+frm_end_date+'"';
  if(to_end_date) cond += ' AND `tabAppraisal`.end_date <= "'+to_end_date+'"';
  if(fiscal_year !='') cond += ' AND `tabAppraisal`.fiscal_year = "'+fiscal_year+'"';
  if(approver) cond += ' AND `tabAppraisal`.kra_approver = "'+approver+'"';

  //var q = 'SELECT DISTINCT `tabAppraisal`.name, `tabAppraisal`.status, `tabAppraisal`.employee, `tabAppraisal`.employee_name, `tabAppraisal`.start_date,`tabAppraisal`.end_date,`tabAppraisal`.kra_approver, `tabAppraisal`.total_score FROM `tabAppraisal` WHERE `tabAppraisal`.status= "Submitted" AND `tabAppraisal`.kra_approver = "'+ user+'"'+cond;  
  var q = 'SELECT DISTINCT `tabAppraisal`.name, `tabAppraisal`.employee, `tabAppraisal`.employee_name, `tabAppraisal`.start_date,`tabAppraisal`.end_date,`tabAppraisal`.kra_approver, `tabAppraisal`.total_score FROM `tabAppraisal` WHERE `tabAppraisal`.status= "Submitted"'+cond;  
  return q;
}