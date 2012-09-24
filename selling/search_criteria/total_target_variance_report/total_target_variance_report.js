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
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Territory'+NEWLINE+'Sales Person',report_default:'Territory',ignore : 1,parent:'Target Detail', single_select :1});
  this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Target Detail', single_select :1});
  this.add_filter({fieldname:'under', label:'Under',fieldtype:'Select', options:'Sales Order'+NEWLINE+'Delivery Note'+NEWLINE+'Sales Invoice',report_default:'Sales Order',ignore : 1, parent:'Target Detail', single_select :1});
  this.add_filter({fieldname : 'target_on', label:'Target On', fieldtype:'Select', options:'Quantity'+NEWLINE+'Amount',report_default:'Quantity',ignore : 1,parent:'Target Detail', single_select :1});
}
report.aftertableprint = function(t) {
   $yt(t,'*',1,{whiteSpace:'pre'});
}
this.mytabs.items['Select Columns'].hide();