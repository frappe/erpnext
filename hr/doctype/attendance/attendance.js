cur_frm.add_fetch('employee', 'company', 'company');	

//get employee's name based on employee id selected
cur_frm.cscript.employee = function(doc,cdt,cdn){
  if(doc.employee) get_server_fields('get_emp_name', '', '', doc, cdt, cdn, 1);
  refresh_field('employee_name'); 
}


//Employee
//-----------------------------
cur_frm.fields_dict['employee'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabEmployee`.`name` FROM `tabEmployee` WHERE `tabEmployee`.status = "Active" AND `tabEmployee`.`docstatus`!= 2 AND `tabEmployee`.%(key)s LIKE "%s"  ORDER BY `tabEmployee`.`name` ASC LIMIT 50';
}
