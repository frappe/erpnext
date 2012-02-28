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

var get_month = function(){

  var dict = {0:'Jan', 1:'Feb',2:'Mar',3:'Apr',4:'May',5:'June',6:'July',7:'Aug',8:'Sept',9:'Oct',10:'Nov',11:'Dec'}
  var d = new Date();
  return dict[d.getMonth()]

}

report.customize_filters = function() {
  this.hide_all_filters();
  this.add_filter({fieldname:'month', label:'Month', fieldtype:'Select', options:'Jan'+NEWLINE+'Feb'+NEWLINE+'Mar'+NEWLINE+'Apr'+NEWLINE+'May'+NEWLINE+'June'+NEWLINE+'July'+NEWLINE+'Aug'+NEWLINE+'Sept'+NEWLINE+'Oct'+NEWLINE+'Nov'+NEWLINE+'Dec',ignore : 1,parent:'Attendance', single_select:1});
  
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Employee'].df.filter_hide = 0;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Month'].df.filter_hide = 0;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Company'].df.filter_hide = 0;
  
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Employee'].df.in_first_page = 1;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Month'].df.in_first_page = 1;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Fiscal Year'].df.in_first_page = 1;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Company'].df.in_first_page = 1;
  
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Month'].df['report_default'] = get_month();
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
  this.get_filter('Attendance', 'Fiscal Year').set_as_single();
}
this.mytabs.items['More Filters'].hide();
this.mytabs.items['Select Columns'].hide();