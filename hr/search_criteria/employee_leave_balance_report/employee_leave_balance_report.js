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

this.mytabs.items['Select Columns'].hide();

this.mytabs.tabs['More Filters'].hide();

report.customize_filters = function() {
	this.add_filter({
		fieldname:'fiscal_year',
		label:'Fiscal Year', 
		fieldtype:'Link',
		ignore : 1,
		options: 'Fiscal Year',
		parent:'Leave Allocation',
		in_first_page:1,
		report_default: sys_defaults.fiscal_year
	});
	this.add_filter({
		fieldname:'employee_name',
		label:'Employee Name', 
		fieldtype:'Data',
		ignore : 1,
		options: '',
		parent:'Leave Allocation',
		in_first_page:1
	});
}