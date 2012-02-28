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

  this.add_filter({fieldname:'posting_date', label:'Posting Date', fieldtype:'Date', ignore : 1, parent:'Item'});
  //this.add_filter({fieldname:'weekly_working_days', label:'Weekly Working Days', fieldtype:'Select', options:NEWLINE+1+NEWLINE+2+NEWLINE+3+NEWLINE+4+NEWLINE+5+NEWLINE+6+NEWLINE+7, ignore : 1, parent:'Item'});

  this.filter_fields_dict['Item'+FILTER_SEP +'From Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['Item'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;
  //this.filter_fields_dict['Item'+FILTER_SEP +'Weekly Working Days'].df.in_first_page = 1;


}