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

//-------------------------- Onload ---------------------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
  if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
}

//-------------------  Get Contact Person based on customer selected ---------------------------
cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  if(doc.customer)
    return 'SELECT `tabContact`.contact_name FROM `tabContact` WHERE (`tabContact`.is_customer = 1 AND `tabContact`.customer_name = "'+ doc.customer+'") AND `tabContact`.docstatus != 2 AND `tabContact`.contact_name LIKE "%s" ORDER BY `tabContact`.contact_name ASC LIMIT 50';
  else
    msgprint("Please select Customer first")
}

//-------------------------------- get query select Territory ------------------------------------------
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
}

//------------------------ Customer and its primary contact Details ------------------------------------
cur_frm.cscript.customer = function(doc, cdt, cdn) {
  if(doc.customer) get_server_fields('get_customer_details', '','', doc, cdt, cdn, 1);
}

//--------------------- Customer's Contact Person Details --------------------------------------------
cur_frm.cscript.contact_person = function(doc, cdt, cdn) {
  if(doc.contact_person) {
    get_server_fields('get_contact_details','','',doc, cdt, cdn, 1);
  }
}

//--------- calculate gross profit --------------------------------
cur_frm.cscript.project_value = function(doc, cdt, cdn){
  get_server_fields('get_gross_profit','','',doc, cdt, cdn, 1);
}

//--------- calculate gross profit --------------------------------
cur_frm.cscript.est_material_cost = function(doc, cdt, cdn){
  get_server_fields('get_gross_profit','','',doc, cdt, cdn, 1);
}
