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

cur_frm.cscript.onload = function(doc, dt, dn) {
  if(!doc.status) set_multiple(dt,dn,{status:'Draft'});
  
  if(doc.__islocal){
    set_multiple(dt,dn,{transaction_date:get_today()});
    hide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
  }   
}


//customer
cur_frm.cscript.customer = function(doc,dt,dn) {
  var callback = function(r,rt) {
      var doc = locals[cur_frm.doctype][cur_frm.docname];
      cur_frm.refresh();
  }   

  if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 'get_default_customer_address', '', callback);
  if(doc.customer) unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
}

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {    
  if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
  return 'SELECT name,address_line1,city FROM tabAddress WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  return 'SELECT name,CONCAT(first_name," ",ifnull(last_name,"")) As FullName,department,designation FROM tabContact WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

//
cur_frm.fields_dict['item_maintenance_detail'].grid.get_field('item_code').get_query = function(doc, cdt, cdn) {
  return 'SELECT tabItem.name,tabItem.item_name,tabItem.description FROM tabItem WHERE tabItem.is_service_item="Yes" AND tabItem.docstatus != 2 AND tabItem.%(key)s LIKE "%s" LIMIT 50';
}

// Get Items based on SO Selected
cur_frm.cscript.get_items = function(doc, dt, dn) {
  var callback = function(r,rt) { 
	  unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
	  cur_frm.refresh();
  }
  get_server_fields('pull_sales_order_detail','','',doc, dt, dn,1,callback);
}


cur_frm.cscript.item_code = function(doc, cdt, cdn) {
  var fname = cur_frm.cscript.fname;
  var d = locals[cdt][cdn];
  if (d.item_code) {
    get_server_fields('get_item_details',d.item_code, 'item_maintenance_detail',doc,cdt,cdn,1);
  }
}

/*
cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabContact`.contact_name FROM `tabContact` WHERE `tabContact`.is_customer = 1 AND `tabContact`.customer = "'+ doc.customer+'" AND `tabContact`.contact_name LIKE "%s" ORDER BY `tabContact`.contact_name ASC LIMIT 50';
}


cur_frm.cscript.customer = function(doc, cdt, cdn) {
  get_server_fields('get_customer_details','','',doc, cdt, cdn, 1);
}
*/

cur_frm.fields_dict['sales_order_no'].get_query = function(doc) {
  doc = locals[this.doctype][this.docname];
  var cond = '';
  if(doc.customer) {
    cond = '`tabSales Order`.customer = "'+doc.customer+'" AND';
  }
  return repl('SELECT DISTINCT `tabSales Order`.name FROM `tabSales Order`, `tabSales Order Item`, `tabItem` WHERE `tabSales Order`.company = "%(company)s" AND `tabSales Order`.docstatus = 1 AND `tabSales Order Item`.parent = `tabSales Order`.name AND `tabSales Order Item`.item_code = `tabItem`.name AND `tabItem`.is_service_item = "Yes" AND %(cond)s `tabSales Order`.name LIKE "%s" ORDER BY `tabSales Order`.name DESC LIMIT 50', {company:doc.company, cond:cond});
}

cur_frm.cscript.periodicity = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.start_date && d.end_date){
    arg = {}
    arg.start_date = d.start_date;
    arg.end_date = d.end_date;
    arg.periodicity = d.periodicity;
    get_server_fields('get_no_of_visits',docstring(arg),'item_maintenance_detail',doc, cdt, cdn, 1);
  }
  else{
    msgprint("Please enter Start Date and End Date");
  }
}

cur_frm.cscript.generate_schedule = function(doc, cdt, cdn) {
  if (!doc.__islocal) {
    $c('runserverobj', args={'method':'generate_schedule', 'docs':wn.model.compress(make_doclist(cdt,cdn))},
      function(r,rt){
        refresh_field('maintenance_schedule_detail');
      }
    );
  } else {
    alert("Please save the document before generating maintenance schedule");
  }  
}

//get query select Territory
//=======================================================================================================================
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
}

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;