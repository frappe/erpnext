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
 
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'ID'].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Owner'].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Saved'].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Submitted'].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Cancelled'].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Grand Total >='].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Grand Total <='].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Sales Partner'].df.filter_hide = 1;
  this.filter_fields_dict['Sales Invoice'+FILTER_SEP +'Is Opening Entry'].df.filter_hide = 1;
}
