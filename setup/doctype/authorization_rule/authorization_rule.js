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

 

//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
   
}

// Settings Module

cur_frm.cscript.refresh = function(doc,cdt,cdn){
   

  if(doc.based_on == 'Grand Total' || doc.based_on == 'Average Discount' || doc.based_on == 'Not Applicable') hide_field('master_name');
  else  unhide_field('master_name');
  
  if(doc.based_on == 'Not Applicable') hide_field('value');
  else unhide_field('value');
  
  if(doc.transaction == 'Appraisal'){
    hide_field(['master_name','system_role', 'system_user']);
    unhide_field(['to_emp','to_designation']);
    if(doc.transaction == 'Appraisal') hide_field('value');
    else unhide_field('value');
  }
  else {
    unhide_field(['master_name','system_role', 'system_user','value']);
    hide_field(['to_emp','to_designation']);
  }
}

cur_frm.cscript.based_on = function(doc){
  if(doc.based_on == 'Grand Total' || doc.based_on == 'Average Discount' || doc.based_on == 'Not Applicable'){
    doc.master_name = '';
    refresh_field('master_name');
    hide_field('master_name');
  }
  else{
    unhide_field('master_name');
  }
  
  if(doc.based_on == 'Not Applicable') {
      doc.value =0;
      refresh_field('value');
      hide_field('value');
    }
    else unhide_field('value');
}

cur_frm.cscript.transaction = function(doc,cdt,cdn){
  if (doc.transaction == 'Appraisal'){
    doc.master_name = doc.system_role = doc.system_user = '';
    refresh_many(['master_name','system_role', 'system_user']);
    hide_field(['master_name','system_role', 'system_user']);
    unhide_field(['to_emp','to_designation']);
	doc.value =0;
    refresh_many('value');
    hide_field('value');
  }
  else {
    unhide_field(['master_name','system_role', 'system_user','value']);
    hide_field(['to_emp','to_designation']);
  }
  
  if(doc.transaction == 'Appraisal') doc.based_on == 'Not Applicable';
}


cur_frm.fields_dict.system_user.get_query = erpnext.utils.profile_query;

cur_frm.fields_dict.approving_user.get_query = erpnext.utils.profile_query;

// System Role Trigger
// -----------------------
cur_frm.fields_dict['system_role'].get_query = function(doc) {
  return 'SELECT tabRole.name FROM tabRole WHERE tabRole.name not in ("Administrator","Guest","All") AND tabRole.%(key)s LIKE "%s" LIMIT 50'
}

// Approving Role Trigger
// -----------------------
cur_frm.fields_dict['approving_role'].get_query = function(doc) {
  return 'SELECT tabRole.name FROM tabRole WHERE tabRole.name not in ("Administrator","Guest","All") AND tabRole.%(key)s LIKE "%s" LIMIT 50'
}


// Master Name Trigger
// --------------------
cur_frm.fields_dict['master_name'].get_query = function(doc){
  if(doc.based_on == 'Customerwise Discount')
    return 'SELECT `tabCustomer`.`name` FROM `tabCustomer` WHERE `tabCustomer`.docstatus !=2 and `tabCustomer`.`name` LIKE "%s" ORDER BY `tabCustomer`.`name` DESC LIMIT 50';
  else if(doc.based_on == 'Itemwise Discount')
    return 'SELECT `tabItem`.`name` FROM `tabItem` WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` = "0000-00-00" OR `tabItem`.`end_of_life` > NOW()) and `tabItem`.is_sales_item = "Yes" and tabItem.%(key)s LIKE "%s" ORDER BY `tabItem`.`name` DESC LIMIT 50';
  else
    return 'SELECT `tabItem`.`name` FROM `tabItem` WHERE `tabItem`.`name` = "cheating done to avoid null" ORDER BY `tabItem`.`name` DESC LIMIT 50';
}

cur_frm.fields_dict.to_emp.get_query = erpnext.utils.employee_query;