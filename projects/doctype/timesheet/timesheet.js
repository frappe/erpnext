
// ======================= OnLoad =============================================
cur_frm.cscript.onload = function(doc,cdt,cdn){  
  if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
  if(!doc.timesheet_date) set_multiple(cdt,cdn,{timesheet_date:get_today()});
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){}


cur_frm.fields_dict['timesheet_details'].grid.get_field("project_name").get_query = function(doc,cdt,cdn){
  var cond=cond1='';
  var d = locals[cdt][cdn];
  //if(d.customer_name) cond = 'ifnull(`tabProject`.customer_name, "") = "'+d.customer_name+'" AND';
  if(d.task_id) cond1 = 'ifnull(`tabTicket`.project, "") = `tabProject`.name AND `tabTicket`.name = "'+d.task_id+'" AND';
  
  return repl('SELECT distinct `tabProject`.`name` FROM `tabProject`, `tabTicket` WHERE %(cond1)s `tabProject`.`name` LIKE "%s" ORDER BY `tabProject`.`name` ASC LIMIT 50', {cond1:cond1});
}

cur_frm.cscript.task_name = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.task_name) get_server_fields('get_task_details', d.task_name, 'timesheet_details', doc, cdt, cdn, 1);
}

cur_frm.fields_dict['timesheet_details'].grid.get_field("task_name").get_query = function(doc,cdt,cdn){
  var cond='';
  var d = locals[cdt][cdn];
  if(d.project_name) cond = 'ifnull(`tabTicket`.project, "") = "'+d.project_name+'" AND';
  
  return repl('SELECT distinct `tabTicket`.`subject` FROM `tabTicket` WHERE %(cond)s `tabTicket`.`subject` LIKE "%s" ORDER BY `tabTicket`.`subject` ASC LIMIT 50', {cond:cond});
}