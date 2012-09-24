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
  filter_list = ['Debit To', 'From Posting Date', 'To Posting Date']
  for(var i=0;i<filter_list.length;i++) 
    this.filter_fields_dict['Sales Invoice'+FILTER_SEP +filter_list[i]].df.filter_hide = 0;

  this.filter_fields_dict['Sales Invoice Item'+FILTER_SEP +'Item'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Invoice Item'+FILTER_SEP +'Item Group'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Invoice Item'+FILTER_SEP +'Brand Name'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Invoice Item'+FILTER_SEP +'Cost Center'].df.filter_hide = 0;

  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'From Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['Sales Invoice Item'+FILTER_SEP +'Item'].df.in_first_page = 1;

  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Company'].df['report_default']=sys_defaults.company
}
