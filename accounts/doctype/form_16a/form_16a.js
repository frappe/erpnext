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
  if(doc.company)get_server_fields('get_registration_details','','',doc,cdt,cdn,1);
}

cur_frm.cscript.company = function(doc,cdt,cdn){
  if(doc.company)get_server_fields('get_registration_details','','',doc,cdt,cdn);
}

cur_frm.fields_dict['party_name'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.master_type = "Supplier" AND `tabAccount`.docstatus != 2 AND `tabAccount`.group_or_ledger = "Ledger" AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.name ASC LIMIT 50';
}

cur_frm.cscript.party_name = function(doc,cdt,cdn){
  if(doc.party_name)get_server_fields('get_party_det','','',doc,cdt,cdn);
}

// Date validation
cur_frm.cscript.to_date = function(doc,cdt,cdn){
  if((doc.from_date) && (doc.to_date) && (doc.from_date>doc.to_date)){
    alert("From date can not be greater than To date");
    doc.to_date='';
    refresh_field('to_date');
  }
}

cur_frm.cscript.from_date = function(doc,cdt,cdn){
  if((doc.from_date) && (doc.to_date) && (doc.from_date>doc.to_date)){
    alert("From date can not be greater than To date");
    doc.from_date='';
    refresh_field('from_date');
  }
}