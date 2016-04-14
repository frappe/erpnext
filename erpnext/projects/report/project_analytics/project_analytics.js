frappe.require("assets/erpnext/js/project_statements.js");

frappe.query_reports["Project Analytics"] = {
	"filters": [
        {
			fieldname:"company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1,
			"on_change": function(query_report) {
					query_report.filters_by_name.week_range.set_input('');
					query_report.trigger_refresh();
			}
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			"reqd": 1,
			"on_change": function(query_report) {
					query_report.filters_by_name.week_range.set_input('');
					query_report.trigger_refresh();
			}
		},
		{
			"fieldname": "week_range",
			"label": __("Week Range"),
			"fieldtype": "Link",
			"options": "Week Range",
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.get_week_range"
				}
			},
			"on_change": function(query_report) {
				var week_range = query_report.get_values().week_range;
				if (!week_range) {
					return;
				}
				frappe.model.with_doc("Week Range", week_range, function(r) {
					var wr = frappe.model.get_doc("Week Range", week_range);
					query_report.filters_by_name.from_date.set_input(wr.start_date);
					query_report.filters_by_name.to_date.set_input(wr.end_date);
					query_report.trigger_refresh();
				});
			}
		},
		{
			"fieldtype": "Break",
		},
		{
			"fieldtype": "Link",
			"fieldname": "employee",
			"options": "Week Range",
			"label": __("Employee"),
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.employee_query"
				}
			}
		},
		{
			"fieldtype": "Link",
			"fieldname": "worked_on",
			"options": "Project",
			"label": __("Worked On"),
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.get_worked_on"
				}
			}
		},
		{
			"fieldtype": "Link",
			"fieldname": "activity",
			"options": "Activity Type",
			"label": __("Activity Type"),
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.get_activity_type"
				}
			}
		}
	],
	"formatter": erpnext.project_statements.formatter,
	"tree": true,
	"name_field": "row_labels",
	"parent_field": "parent_labels",
	"initial_depth": 3
}
