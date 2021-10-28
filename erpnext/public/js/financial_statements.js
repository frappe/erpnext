frappe.provide("erpnext.financial_statements");

erpnext.financial_statements = {
	"filters": get_filters(),
	"formatter": function(value, row, column, data, default_formatter) {
		if (data && column.fieldname=="account") {
			value = data.account_name || value;

			column.link_onclick =
				"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
			column.is_tree = true;
		}

		value = default_formatter(value, row, column, data);

		if (data && !data.parent_account) {
			value = $(`<span>${value}</span>`);

			var $value = $(value).css("font-weight", "bold");
			if (data.warn_if_negative && data[column.fieldname] < 0) {
				$value.addClass("text-danger");
			}

			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
	"open_general_ledger": function(data) {
		if (!data.account) return;
		var project = $.grep(frappe.query_report.filters, function(e){ return e.df.fieldname == 'project'; })

		frappe.route_options = {
			"account": data.account,
			"company": frappe.query_report.get_filter_value('company'),
			"from_date": data.from_date || data.year_start_date,
			"to_date": data.to_date || data.year_end_date,
			"project": (project && project.length > 0) ? project[0].$input.val() : ""
		};
		frappe.set_route("query-report", "General Ledger");
	},
	"tree": true,
	"name_field": "account",
	"parent_field": "parent_account",
	"initial_depth": 3,
	onload: function(report) {
		// dropdown for links to other financial statements
		erpnext.financial_statements.filters = get_filters()

		let fiscal_year = frappe.defaults.get_user_default("fiscal_year")

		frappe.model.with_doc("Fiscal Year", fiscal_year, function(r) {
			var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
			frappe.query_report.set_filter_value({
				period_start_date: fy.year_start_date,
				period_end_date: fy.year_end_date
			});
		});

		const views_menu = report.page.add_custom_button_group(__('Financial Statements'));

		report.page.add_custom_menu_item(views_menu, __("Balance Sheet"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Balance Sheet', {company: filters.company});
		});

		report.page.add_custom_menu_item(views_menu, __("Profit and Loss"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Profit and Loss Statement', {company: filters.company});
		});

		report.page.add_custom_menu_item(views_menu, __("Cash Flow Statement"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Cash Flow', {company: filters.company});
		});
	}
};

function get_filters() {
	let filters = [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"finance_book",
			"label": __("Finance Book"),
			"fieldtype": "Link",
			"options": "Finance Book"
		},
		{
			"fieldname":"filter_based_on",
			"label": __("Filter Based On"),
			"fieldtype": "Select",
			"options": ["Fiscal Year", "Date Range"],
			"default": ["Fiscal Year"],
			"reqd": 1,
			on_change: function() {
				let filter_based_on = frappe.query_report.get_filter_value('filter_based_on');
				frappe.query_report.toggle_filter_display('from_fiscal_year', filter_based_on === 'Date Range');
				frappe.query_report.toggle_filter_display('to_fiscal_year', filter_based_on === 'Date Range');
				frappe.query_report.toggle_filter_display('period_start_date', filter_based_on === 'Fiscal Year');
				frappe.query_report.toggle_filter_display('period_end_date', filter_based_on === 'Fiscal Year');

				frappe.query_report.refresh();
			}
		},
		{
			"fieldname":"period_start_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"depends_on": "eval:doc.filter_based_on == 'Date Range'"
		},
		{
			"fieldname":"period_end_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"depends_on": "eval:doc.filter_based_on == 'Date Range'"
		},
		{
			"fieldname":"from_fiscal_year",
			"label": __("Start Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1,
			"depends_on": "eval:doc.filter_based_on == 'Fiscal Year'"
		},
		{
			"fieldname":"to_fiscal_year",
			"label": __("End Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1,
			"depends_on": "eval:doc.filter_based_on == 'Fiscal Year'"
		},
		{
			"fieldname": "periodicity",
			"label": __("Periodicity"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Half-Yearly", "label": __("Half-Yearly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			"default": "Yearly",
			"reqd": 1
		},
		// Note:
		// If you are modifying this array such that the presentation_currency object
		// is no longer the last object, please make adjustments in cash_flow.js
		// accordingly.
		{
			"fieldname": "presentation_currency",
			"label": __("Currency"),
			"fieldtype": "Select",
			"options": erpnext.get_presentation_currency_list()
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Cost Center', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		}
	]

	return filters;
}
