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
  
  this.add_filter({fieldname:'approver', label:'Approver', fieldtype:'Link', options:'Profile', ignore : 1, parent:'Expense Claim'});  
  this.filter_fields_dict['Expense Claim'+FILTER_SEP +'Approver'].df.in_first_page = 1;
  
  this.filter_fields_dict['Expense Claim'+FILTER_SEP +'From Employee'].df.filter_hide = 0;
  this.filter_fields_dict['Expense Claim'+FILTER_SEP +'Employee Name'].df.filter_hide = 0;
  this.filter_fields_dict['Expense Claim'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;  
  this.filter_fields_dict['Expense Claim'+FILTER_SEP +'From Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Expense Claim'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Expense Claim'+FILTER_SEP +'Company'].df.filter_hide = 0;
}
this.mytabs.items['Select Columns'].hide();

report.get_query = function(){
  //get filter values
  emp = this.filter_fields_dict['Expense Claim'+FILTER_SEP+'From Employee'].get_value(); 
  emp_nm = this.filter_fields_dict['Expense Claim'+FILTER_SEP+'Employee Name'].get_value(); 
  frm_start_date = this.filter_fields_dict['Expense Claim'+FILTER_SEP+'From Posting Date'].get_value(); 
  to_end_date = this.filter_fields_dict['Expense Claim'+FILTER_SEP+'To Posting Date'].get_value(); 
  fiscal_year = this.filter_fields_dict['Expense Claim'+FILTER_SEP+'Fiscal Year'].get_value();
  approver = this.filter_fields_dict['Expense Claim'+FILTER_SEP+'Approver'].get_value();
  company = this.filter_fields_dict['Expense Claim'+FILTER_SEP+'Company'].get_value();
  
  var cond = '';
  if(emp) cond += ' AND `tabExpense Claim`.employee = "'+emp+'"';
  if(emp_nm) cond += ' AND `tabExpense Claim`.employee_name = "'+emp_nm+'"';
  if(frm_start_date) cond += ' AND `tabExpense Claim`.posting_date >= "'+frm_start_date+'"';
  if(to_end_date) cond += ' AND `tabExpense Claim`.posting_date <= "'+to_end_date+'"';
  if(fiscal_year !='') cond += ' AND `tabExpense Claim`.fiscal_year = "'+fiscal_year+'"';
  if(approver) cond += ' AND `tabExpense Claim`.exp_approver = "'+approver+'"';
  if(company) cond += ' AND `tabExpense Claim`.company = "'+company+'"';

  var q = 'SELECT DISTINCT `tabExpense Claim`.name, `tabExpense Claim`.employee, `tabExpense Claim`.employee_name, `tabExpense Claim`.posting_date,`tabExpense Claim`.exp_approver, `tabExpense Claim`.total_claimed_amount, `tabExpense Claim`.total_sanctioned_amount FROM `tabExpense Claim` WHERE `tabExpense Claim`.approval_status= "Submitted"'+cond;  
  return q;
}