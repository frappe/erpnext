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

  //this.add_filter({fieldname:'item_code', label:'Item Code', fieldtype:'Link', options:'Item',ignore : 1,parent:'Delivery Note Item'});

  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Project Name'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;  
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Customer'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Customer Name'].df.filter_hide = 0;

  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Project Name'].df.in_first_page = 1;

  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
}
