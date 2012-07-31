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
  this.add_filter({fieldname:'item_name', label:'Item Name', fieldtype:'Data', options:'', parent:'Item', in_first_page : 0});
  this.add_filter({fieldname:'description', label:'Description', fieldtype:'Small Text', options: '', parent:'Item', in_first_page : 0});
  this.add_filter({fieldname:'item_group', label:'Item Group', fieldtype:'link', options: 'Item Group', parent:'Item', in_first_page : 1});
  this.add_filter({fieldname:'brand', label:'Brand', fieldtype:'link', options: 'Brand', parent:'Item', in_first_page : 1});
}