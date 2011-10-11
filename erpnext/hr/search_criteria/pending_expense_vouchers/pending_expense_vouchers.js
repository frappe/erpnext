report.customize_filters = function() {
  this.hide_all_filters();  
  
  this.add_filter({fieldname:'approver', label:'Approver', fieldtype:'Link', options:'Profile', ignore : 1, parent:'Expense Voucher'});  
  this.filter_fields_dict['Expense Voucher'+FILTER_SEP +'Approver'].df.in_first_page = 1;
  
  this.filter_fields_dict['Expense Voucher'+FILTER_SEP +'From Employee'].df.filter_hide = 0;
  this.filter_fields_dict['Expense Voucher'+FILTER_SEP +'Employee Name'].df.filter_hide = 0;
  this.filter_fields_dict['Expense Voucher'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;  
  this.filter_fields_dict['Expense Voucher'+FILTER_SEP +'From Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Expense Voucher'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Expense Voucher'+FILTER_SEP +'Company'].df.filter_hide = 0;
}
this.mytabs.items['Select Columns'].hide();

report.get_query = function(){
  //get filter values
  emp = this.filter_fields_dict['Expense Voucher'+FILTER_SEP+'From Employee'].get_value(); 
  emp_nm = this.filter_fields_dict['Expense Voucher'+FILTER_SEP+'Employee Name'].get_value(); 
  frm_start_date = this.filter_fields_dict['Expense Voucher'+FILTER_SEP+'From Posting Date'].get_value(); 
  to_end_date = this.filter_fields_dict['Expense Voucher'+FILTER_SEP+'To Posting Date'].get_value(); 
  fiscal_year = this.filter_fields_dict['Expense Voucher'+FILTER_SEP+'Fiscal Year'].get_value();
  approver = this.filter_fields_dict['Expense Voucher'+FILTER_SEP+'Approver'].get_value();
  company = this.filter_fields_dict['Expense Voucher'+FILTER_SEP+'Company'].get_value();
  
  var cond = '';
  if(emp) cond += ' AND `tabExpense Voucher`.employee = "'+emp+'"';
  if(emp_nm) cond += ' AND `tabExpense Voucher`.employee_name = "'+emp_nm+'"';
  if(frm_start_date) cond += ' AND `tabExpense Voucher`.posting_date >= "'+frm_start_date+'"';
  if(to_end_date) cond += ' AND `tabExpense Voucher`.posting_date <= "'+to_end_date+'"';
  if(fiscal_year !='') cond += ' AND `tabExpense Voucher`.fiscal_year = "'+fiscal_year+'"';
  if(approver) cond += ' AND `tabExpense Voucher`.exp_approver = "'+approver+'"';
  if(company) cond += ' AND `tabExpense Voucher`.company = "'+company+'"';

  var q = 'SELECT DISTINCT `tabExpense Voucher`.name, `tabExpense Voucher`.employee, `tabExpense Voucher`.employee_name, `tabExpense Voucher`.posting_date,`tabExpense Voucher`.exp_approver, `tabExpense Voucher`.total_claimed_amount, `tabExpense Voucher`.total_sanctioned_amount FROM `tabExpense Voucher` WHERE `tabExpense Voucher`.approval_status= "Submitted"'+cond;  
  return q;
}