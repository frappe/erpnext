// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

const get_currencies = () => {
	// frappe.db.get_list returns a Promise
	return frappe.db.get_list('GL Entry',
		{
			distinct: true,
			fields:['account_currency'],
			as_list: true
		}
	);
}

const flatten = (array) => {
	return [].concat.apply([], array);
}

const show_report = (currency_list) => {
	frappe.query_reports["General Ledger"] = {
		"filters": [
			{
				"fieldname":"company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company"),
				"reqd": 1
			},
			{
				"fieldname":"from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
				"reqd": 1,
				"width": "60px"
			},
			{
				"fieldname":"to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.get_today(),
				"reqd": 1,
				"width": "60px"
			},
			{
				"fieldname":"account",
				"label": __("Account"),
				"fieldtype": "Link",
				"options": "Account",
				"get_query": function() {
					var company = frappe.query_report_filters_by_name.company.get_value();
					return {
						"doctype": "Account",
						"filters": {
							"company": company,
						}
					}
				}
			},
			{
				"fieldname":"voucher_no",
				"label": __("Voucher No"),
				"fieldtype": "Data",
			},
			{
				"fieldname":"project",
				"label": __("Project"),
				"fieldtype": "Link",
				"options": "Project"
			},
			{
				"fieldtype": "Break",
			},
			{
				"fieldname":"party_type",
				"label": __("Party Type"),
				"fieldtype": "Link",
				"options": "Party Type",
				"default": ""
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
				},
				on_change: function() {
					var party_type = frappe.query_report_filters_by_name.party_type.get_value();
					var party = frappe.query_report_filters_by_name.party.get_value();
					if(!party_type || !party) {
						frappe.query_report_filters_by_name.party_name.set_value("");
						return;
					}

					var fieldname = frappe.scrub(party_type) + "_name";
					frappe.db.get_value(party_type, party, fieldname, function(value) {
						frappe.query_report_filters_by_name.party_name.set_value(value[fieldname]);
					});
				}
			},
			{
				"fieldname":"party_name",
				"label": __("Party Name"),
				"fieldtype": "Data",
				"hidden": 1
			},
			{
				"fieldname":"group_by_voucher",
				"label": __("Group by Voucher"),
				"fieldtype": "Check",
				"default": 1
			},
			{
				"fieldname":"group_by_account",
				"label": __("Group by Account"),
				"fieldtype": "Check",
			},
			{
				"fieldname": "presentation_currency",
				"label": __("Currency"),
				"fieldtype": "Select",
				"options": currency_list
			}
		]
	}
}

get_currencies()
.then((currency_list) => flatten(currency_list))
.then((currency_list) => show_report(currency_list));