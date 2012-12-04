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
		order by \
		case when name like \"%s%%\" then 0 else 1 end, \
		case when concat_ws(' ', first_name, middle_name, last_name) like \"%s%%\" \
			then 0 else 1 end, \
		name asc limit 50";
};

// searches for active employees
erpnext.utils.employee_query = function() {
	return "select name, employee_name from `tabEmployee` \
		where status = 'Active' and docstatus < 2 and \
		(%(key)s like \"%s\" or employee_name like \"%%%s\") \
		order by \
		case when name like \"%s%%\" then 0 else 1 end, \
		case when employee_name like \"%s%%\" then 0 else 1 end, \
		name limit 50";
};

// searches for leads which are not converted
erpnext.utils.lead_query = function() {
	return "select name, lead_name, company_name from `tabLead` \
		where docstatus < 2 and ifnull(status, '') != 'Converted' and \
		(%(key)s like \"%s\" or lead_name like \"%%%s\" or company_name like \"%%%s\") \
		order by \
		case when name like \"%s%%\" then 0 else 1 end, \
		case when lead_name like \"%s%%\" then 0 else 1 end, \
		case when company_name like \"%s%%\" then 0 else 1 end, \
		lead_name asc limit 50";
};

// searches for customer
erpnext.utils.customer_query = function() {
	if(sys_defaults.cust_master_name == "Customer Name") {
		var fields = ["name", "customer_group", "country", "territory"];
	} else {
		var fields = ["name", "customer_name", "customer_group", "country", "territory"];
	}
	
	return "select " + fields.join(", ") + " from `tabCustomer` where docstatus < 2 and \
		(%(key)s like \"%s\" or customer_name like \"%%%s\") \
		order by \
		case when name like \"%s%%\" then 0 else 1 end, \
		case when customer_name like \"%s%%\" then 0 else 1 end, \
		name, customer_name limit 50";
};

// searches for supplier
erpnext.utils.supplier_query = function() {
	if(sys_defaults.supp_master_name == "Supplier Name") {
		var fields = ["name", "supplier_type"];
	} else {
		var fields = ["name", "supplier_name", "supplier_type"];
	}
	
	return "select " + fields.join(", ") + " from `tabSupplier` where docstatus < 2 and \
		(%(key)s like \"%s\" or supplier_name like \"%%%s\") \
		order by \
		case when name like \"%s%%\" then 0 else 1 end, \
		case when supplier_name like \"%s%%\" then 0 else 1 end, \
		name, supplier_name limit 50";
};

wn.provide("erpnext.queries");

erpnext.queries.account = function(opts) {
	if(!opts) 
		opts = {};
	if(!opts.group_or_ledger) 
		opts.group_or_ledger = "Ledger";
		
	conditions = [];
	$.each(opts, function(key, val) {
		conditions.push("tabAccount.`" + key + "`='"+esc_quotes(val)+"'");
	});
	
	return 'SELECT tabAccount.name, tabAccount.parent_account, tabAccount.debit_or_credit \
		FROM tabAccount \
		WHERE tabAccount.docstatus!=2 \
		AND tabAccount.%(key)s LIKE "%s" ' + (conditions 
			? (" AND " + conditions.join(" AND "))
			: "")
}