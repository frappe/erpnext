// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Purchase Register"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "company_gstin",
			"label": __("Company GSTIN"),
			"fieldtype": "Select"
		},
		{
			"fieldname":"mode_of_payment",
			"label": __("Mode of Payment"),
			"fieldtype": "Link",
			"options": "Mode of Payment"
		},
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center"
		},
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		}
	],
	onload: function (report) {
		let filters = report.get_values();

		frappe.call({
			method: 'erpnext.accounts.report.sales_register.sales_register.get_company_gstins',
			args: {
				company: filters.company
			},
			callback: function(r) {
				frappe.query_report.page.fields_dict.company_gstin.df.options = r.message;
				frappe.query_report.page.fields_dict.company_gstin.refresh();
			}
		});
	}
}
setTimeout(()=>{
	frappe.query_report.page.fields_dict.company.df.onchange = function(){
		frappe.call({
			method: 'erpnext.accounts.report.sales_register.sales_register.get_company_gstins',
			args: {
				company: frappe.query_report.page.fields_dict.company.get_value() 
			},
			callback: function(r) {
				frappe.query_report.page.fields_dict.company_gstin.df.options = r.message;
				frappe.query_report.page.fields_dict.company_gstin.refresh();
			}
		});
	}
}, 100)
erpnext.utils.add_dimensions('Purchase Register', 7);
