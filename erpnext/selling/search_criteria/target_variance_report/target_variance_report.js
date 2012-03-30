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
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Cost Center'+NEWLINE+'Sales Person'+NEWLINE+'Sales Partner',report_default:'Cost Center',ignore : 1,parent:'Target Detail'});
  this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company',report_default:sys_defaults.company, ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'group_by', label:'Group By', fieldtype:'Select', options:NEWLINE+'Item Group',ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'under', label:'Under',fieldtype:'Select', options:'Sales Order'+NEWLINE+'Delivery Note'+NEWLINE+'Sales Invoice',report_default:'Sales Order',ignore : 1, parent:'Target Detail'});

}

report.get_query = function() {
  group_by = '';
  group_by = this.filter_fields_dict['Target Detail'+FILTER_SEP+'Group By'].get_value();
  based_on = this.filter_fields_dict['Target Detail'+FILTER_SEP+'Based On'].get_value();
  sel_fields = '`tabTarget Detail`.parent AS "' + cstr(based_on)+'"';
  cond = ' and ifnull(`tabTarget Detail`.item_group, "") = ""'
  if (group_by == 'Item Group'){
    sel_fields = cstr(sel_fields) + ', `tabTarget Detail`.item_group';
    cond =  ' and ifnull(`tabTarget Detail`.item_group,"") != ""'
  }
  sel_fields = cstr(sel_fields) + ', `tabTarget Detail`.target_amount, `tabTarget Detail`.distribution_id';
  var q = 'SELECT '+ cstr(sel_fields) +' FROM `tabTarget Detail` WHERE `tabTarget Detail`.parenttype = "' + cstr(based_on) + '"'+ cstr(cond);
  return q
}

this.mytabs.items['Select Columns'].hide();