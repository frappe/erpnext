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

cur_frm.cscript.onload = function(doc,cdt,cdn){
  if(!doc.senders_name) {  
    doc.senders_name = user_fullname;
    doc.senders_email = user;
    refresh_many(['senders_name', 'senders_email']);
  }

  if(doc.__islocal) {
    doc.status = 'Open';
    doc.opening_date = get_today();
    refresh_many(['status', 'opening_date']);
  }
  else{
    if(!doc.opening_date){
      doc.opening_date = dateutil.str_to_user(only_date(doc.creation));
      refresh_field('opening_date');      
    }
  }  
  
  //hide unhide field depends on status
  if(doc.status == 'Open') doc.review_date = doc.closing_date = '';
  else if(doc.status == 'Pending Review') doc.closing_date = '';
  refresh_many(['closing_date','review_date']); 

  if(doc.project) cur_frm.cscript.project(doc, cdt, cdn);  
}

cur_frm.cscript.refresh = function(doc,cdt,cdn) {
  cur_frm.clear_custom_buttons();
  if(doc.status == 'Pending Review' && (doc.senders_name == user_fullname || doc.senders_email == user)) {
    cur_frm.add_custom_button('Declare Completed', cur_frm.cscript.declare_completed);
    cur_frm.add_custom_button('Reopen Task', cur_frm.cscript['Reopen Task']);
  }
  if(doc.status == 'Open' && !doc.__islocal) {
    cur_frm.add_custom_button('Cancel Task', cur_frm.cscript['Cancel Task']);
    if(doc.allocated_to == user) cur_frm.add_custom_button('Get Approval', cur_frm.cscript['Get Approval']);
  }
}

cur_frm.fields_dict['project'].get_query = function(doc,cdt,cdn){
  var cond='';
  if(doc.customer) cond = 'ifnull(`tabProject`.customer, "") = "'+doc.customer+'" AND';
  
  return repl('SELECT distinct `tabProject`.`name` FROM `tabProject` WHERE %(cond)s `tabProject`.`name` LIKE "%s" ORDER BY `tabProject`.`name` ASC LIMIT 50', {cond:cond});
}


cur_frm.cscript.project = function(doc, cdt, cdn){
  if(doc.project) get_server_fields('get_project_details', '','', doc, cdt, cdn, 1);
}

cur_frm.fields_dict['customer'].get_query = function(doc,cdt,cdn){
  var cond='';
  if(doc.project) cond = 'ifnull(`tabProject`.customer, "") = `tabCustomer`.name AND ifnull(`tabProject`.name, "") = "'+doc.project+'" AND';
  
  return repl('SELECT distinct `tabCustomer`.`name` FROM `tabCustomer`, `tabProject` WHERE %(cond)s `tabCustomer`.`name` LIKE "%s" ORDER BY `tabCustomer`.`name` ASC LIMIT 50', {cond:cond});
}

cur_frm.cscript.customer = function(doc, cdt, cdn){
  if(doc.customer) get_server_fields('get_customer_details', '','', doc, cdt, cdn, 1);
  else doc.customer_name ='';
}

cur_frm.cscript.allocated_to = function(doc,cdt,cdn){
  get_server_fields('get_allocated_to_name','','',doc,cdt,cdn,1);
}

cur_frm.cscript['Get Approval'] = function(){
  $c_obj(make_doclist(cur_frm.doc.doctype, cur_frm.doc.name), 'set_for_review', '',function(r, rt) {
    if(r.message == 'true'){
      doc.status = 'Pending Review'; //for refresh
      refresh_many(['review_date','status']);
      cur_frm.cscript.refresh(cur_frm.doc, cur_frm.doc.doctype, cur_frm.doc.name);
    }
  });  
}

cur_frm.cscript['Reopen Task'] = function(){
  $c_obj(make_doclist(cur_frm.doc.doctype, cur_frm.doc.name), 'reopen_task', '',function(r, rt) {
    if(r.message == 'true'){
      doc.status = 'Open'; //for refresh
      refresh_many(['status']);
      cur_frm.cscript.refresh(cur_frm.doc, cur_frm.doc.doctype, cur_frm.doc.name);
    }
  });  
}

cur_frm.cscript['Cancel Task'] = function(){
  $c_obj(make_doclist(cur_frm.doc.doctype, cur_frm.doc.name), 'cancel_task', '',function(r, rt) {
    if(r.message == 'true'){
      doc.status = 'Cancelled'; //for refresh
      refresh_many(['status']);
      cur_frm.cscript.refresh(cur_frm.doc, cur_frm.doc.doctype, cur_frm.doc.name);
    }
  });  
}

cur_frm.cscript.declare_completed = function(){
  $c_obj(make_doclist(cur_frm.doc.doctype, cur_frm.doc.name),'declare_completed', '',function(r, rt) {
    if(r.message == 'true'){
      doc.status = 'Closed'; //for refresh
      refresh_many(['review_date', 'closing_date', 'status']);
      cur_frm.cscript.refresh(cur_frm.doc, cur_frm.doc.doctype, cur_frm.doc.name);
    }
  });  
}