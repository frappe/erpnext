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

wn.provide('erpnext.utils');

// searches for enabled profiles
erpnext.utils.profile_query = function() {
	return "select name, concat_ws(' ', first_name, middle_name, last_name) \
		from `tabProfile` where ifnull(enabled, 0)=1 and docstatus < 2 and \
		name not in ('Administrator', 'Guest') and (%(key)s like \"%s\" or \
		concat_ws(' ', first_name, middle_name, last_name) like \"%%%s\") \
		order by name asc limit 50";
};

// searches for active employees
erpnext.utils.employee_query = function() {
	return "select name, employee_name from `tabEmployee` \
		where status = 'Active' and docstatus < 2 and \
		(%(key)s like \"%s\" or employee_name like \"%%%s\") \
		order by name asc limit 50";
};

// searches for leads which are not converted
erpnext.utils.lead_query = function() {
	return "select name, lead_name, company_name from `tabLead` \
		where docstatus < 2 and ifnull(status, '') != 'Converted' and \
		(%(key)s like \"%s\" or lead_name like \"%%%s\" or company_name like \"%%%s\") \
		order by lead_name asc limit 50";
};
