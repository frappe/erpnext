// Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Trial Balance for Party"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1,
			"on_change": function(query_report) {
				var fiscal_year = query_report.get_values().fiscal_year;
				if (!fiscal_year) {
					return;
				}
				frappe.model.with_doc("Fiscal Year", fiscal_year, function(r) {
					var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
					frappe.query_report_filters_by_name.from_date.set_input(fy.year_start_date);
					frappe.query_report_filters_by_name.to_date.set_input(fy.year_end_date);
					query_report.trigger_refresh();
				});
			}
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Select",
			"options": ["Customer", "Supplier","Employee","Imprest Permanent","Imprest Temporary"],
			"default": "Customer",
			"on_change": function(query_report) {
				var party_type = frappe.query_report_filters_by_name.party_type.get_value();
				frappe.query_report_filters_by_name.party_group_or_type.set_value('');
				if(party_type=='Supplier' || party_type=='Customer'){
					document.querySelector("[data-fieldname='party_group_or_type']").style.display = "block";
				}else{
					document.querySelector("[data-fieldname='party_group_or_type']").style.display = "none";
				}

			}
		},
		{
			"fieldname":"party",
			"label": __("Party"),
			"fieldtype": "Dynamic Link",
			"get_options": function() {
				var party_type = frappe.query_report_filters_by_name.party_type.get_value();
				var party = frappe.query_report_filters_by_name.party.get_value();
				if(party && !party_type) {
					frappe.throw(__("Please select Party Type first"));
				}
				return party_type;
			}
		},
		{
		"fieldname":"party_group_or_type",
		"label": __("Party Group or Type"),
		"fieldtype": "Link",
		"options": "Supplier Type",
		"default": "",
		"get_query": function() {
			var party_type = frappe.query_report_filters_by_name.party_type.get_value();
			if(party_type=='Supplier'){
				result = "erpnext.accounts.report.trial_balance_for_party.trial_balance_for_party.get_supplier_type"
			}else if(party_type=='Customer'){
				result = "erpnext.accounts.report.trial_balance_for_party.trial_balance_for_party.get_customer_group"
			}else{
				result= ""
			}

			return {
                query: result
            };

			}
	},

		// {
		// 	"fieldname": "party_group_or_type",
		// 	"label": __("Party Group or Type"),
		// 	"fieldtype": "Dynamic Link",
		// 	"get_options": function() {
		// 		frappe.call({
					
		// 		})
		// 	}
		// },
		{
			"fieldname": "show_zero_values",
			"label": __("Show zero values"),
			"fieldtype": "Check"
		}
	]
}
