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


// ======================= OnLoad =============================================
cur_frm.cscript.onload = function(doc,cdt,cdn){  
  if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
  if(!doc.timesheet_date) set_multiple(cdt,cdn,{timesheet_date:get_today()});
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){
	cur_frm.set_intro("Timesheets will soon be removed. Please create a new Time Log. To create \
	 a new Time Log, to to Projects > Time Log > New Time Log. This will be removed in a few days.")
}


cur_frm.fields_dict['timesheet_details'].grid.get_field("project_name").get_query = function(doc,cdt,cdn){
  var cond=cond1='';
  var d = locals[cdt][cdn];
  //if(d.customer_name) cond = 'ifnull(`tabProject`.customer_name, "") = "'+d.customer_name+'" AND';
  if(d.task_id) cond1 = 'ifnull(`tabTask`.project, "") = `tabProject`.name AND `tabTask`.name = "'+d.task_id+'" AND';
  
  return repl('SELECT distinct `tabProject`.`name` FROM `tabProject`, `tabTask` WHERE %(cond1)s `tabProject`.`name` LIKE "%s" ORDER BY `tabProject`.`name` ASC LIMIT 50', {cond1:cond1});
}

cur_frm.cscript.task_name = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.task_name) get_server_fields('get_task_details', d.task_name, 'timesheet_details', doc, cdt, cdn, 1);
}

cur_frm.fields_dict['timesheet_details'].grid.get_field("task_name").get_query = function(doc,cdt,cdn){
  var cond='';
  var d = locals[cdt][cdn];
  if(d.project_name) cond = 'ifnull(`tabTask`.project, "") = "'+d.project_name+'" AND';
  
  return repl('SELECT distinct `tabTask`.`subject` FROM `tabTask` WHERE %(cond)s `tabTask`.`subject` LIKE "%s" ORDER BY `tabTask`.`subject` ASC LIMIT 50', {cond:cond});
}

cur_frm.fields_dict.timesheet_details.grid.get_field("customer_name").get_query = 
	erpnext.utils.customer_query;