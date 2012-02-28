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

  //to hide all filters
  this.hide_all_filters();

  // to unhide required filters
  this.filter_fields_dict['Stock Entry'+FILTER_SEP +'ID'].df.filter_hide = 0;
  this.filter_fields_dict['Stock Entry'+FILTER_SEP +'Production Order'].df.filter_hide = 0;

  this.filter_fields_dict['Stock Entry'+FILTER_SEP +'From Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Stock Entry'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;

  this.filter_fields_dict['Stock Entry Detail'+FILTER_SEP +'Target Warehouse'].df.filter_hide = 0;

  this.filter_fields_dict['Stock Entry Detail'+FILTER_SEP +'Item Code'].df.filter_hide = 0;
}