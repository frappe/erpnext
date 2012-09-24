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
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Budget Detail'});
  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link',  options:'Company', report_default:sys_defaults.company, ignore : 1, parent:'Budget Detail', in_first_page:1});
  this.filter_fields_dict['Budget Detail'+FILTER_SEP +'Fiscal Year'].df.in_first_page = 1;
  this.filter_fields_dict['Budget Detail'+FILTER_SEP +'Period'].df.in_first_page = 1;

  this.filter_fields_dict['Budget Detail'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
}

report.aftertableprint = function(t) {
   $yt(t,'*',1,{whiteSpace:'pre'});
}

this.mytabs.items['More Filters'].hide();
this.mytabs.items['Select Columns'].hide();
