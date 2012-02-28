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
  this.mytabs.items['Select Columns'].hide()
  this.hide_all_filters();
  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company', report_default:sys_defaults.company, ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'from_fiscal_year', label:'From Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'to_fiscal_year', label:'To Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'date', label:'Date', fieldtype:'Date', options:'',ignore : 1, parent:'Profile'});
}

report.aftertableprint = function(t) {
   $yt(t,'*',1,{NEWLINE:'<br>'});
}