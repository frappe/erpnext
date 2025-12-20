frappe.provide("erpnext.financial_statements");

erpnext.financial_statements = {
	filters: get_filters(),
	baseData: null,
	formatter: function (value, row, column, data, default_formatter, filter) {
		const report_params = [value, row, column, data, default_formatter, filter];
		// Growth/Margin
		if (erpnext.financial_statements._is_special_view(column, data))
			return erpnext.financial_statements._format_special_view(...report_params);

		if (frappe.query_report.get_filter_value("report_template"))
			return erpnext.financial_statements._format_custom_report(...report_params);

		if (frappe.query_report.get_filter_value("report_template"))
			return erpnext.financial_statements._format_custom_report(...report_params);
		else return erpnext.financial_statements._format_standard_report(...report_params);
	},

	_is_special_view: function (column, data) {
		if (!data) return false;
		const view = frappe.query_report.get_filter_value("selected_view");
		return (view === "Growth" && column.colIndex >= 3) || (view === "Margin" && column.colIndex >= 2);
	},

	_format_custom_report: function (value, row, column, data, default_formatter, filter) {
		const columnInfo = erpnext.financial_statements._parse_column_info(column.fieldname, data);
		const formatting = erpnext.financial_statements._get_formatting_for_column(data, columnInfo);

		if (columnInfo.isAccount) {
			return erpnext.financial_statements._format_custom_account_column(
				value,
				data,
				formatting,
				column,
				default_formatter,
				row
			);
		} else {
			return erpnext.financial_statements._format_custom_value_column(
				value,
				data,
				formatting,
				column,
				default_formatter,
				row
			);
		}
	},

	_parse_column_info: function (fieldname, data) {
		const valueMatch = fieldname.match(/^(?:seg_(\d+)_)?(.+)$/);

		const periodKeys = data._segment_info?.period_keys || [];
		const baseName = valueMatch ? valueMatch[2] : fieldname;
		const isPeriodColumn = periodKeys.includes(baseName);

		return {
			isAccount: baseName === "account",
			isPeriod: isPeriodColumn,
			segmentIndex: valueMatch && valueMatch[1] ? parseInt(valueMatch[1]) : null,
			fieldname: baseName,
		};
	},

	_get_formatting_for_column: function (data, columnInfo) {
		let formatting = {};

		if (columnInfo.segmentIndex !== null && data.segment_values)
			formatting = data.segment_values[`seg_${columnInfo.segmentIndex}`] || {};
		else formatting = data;

		return formatting;
	},

	_format_custom_account_column: function (value, data, formatting, column, default_formatter, row) {
		if (!value) return "";

		// Link to open ledger
		const should_link_to_ledger =
			formatting.is_detail || (formatting.account_filters && formatting.child_accounts);

		if (should_link_to_ledger) {
			const glData = {
				account: formatting.account_name || formatting.child_accounts || value,
				from_date: formatting.from_date || formatting.period_start_date,
				to_date: formatting.to_date || formatting.period_end_date,
				account_type: formatting.account_type,
				company: frappe.query_report.get_filter_value("company"),
			};

			column.link_onclick =
				"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(glData) + ")";

			value = default_formatter(value, row, column, data);
		}

		let formattedValue = String(value);

		// Prefix
		if (formatting.is_detail || formatting.prefix)
			formattedValue = (formatting.prefix || "• ") + formattedValue;

		// Indent
		if (data._segment_info && data._segment_info.total_segments === 1) {
			column.is_tree = true;
		} else if (formatting.indent && formatting.indent > 0) {
			const indent = "&nbsp;".repeat(formatting.indent * 4);
			formattedValue = indent + formattedValue;
		}

		// Style
		return erpnext.financial_statements._style_custom_value(formattedValue, formatting, null);
	},

	_format_custom_value_column: function (value, data, formatting, column, default_formatter, row) {
		if (formatting.is_blank_line) return "";

		const col = { ...column };
		col.fieldtype = formatting.fieldtype || col.fieldtype;
		// Avoid formatting as currency
		if (col.fieldtype === "Float") col.options = null;

		let formattedValue = default_formatter(value, row, col, data);
		return erpnext.financial_statements._style_custom_value(formattedValue, formatting, value);
	},

	_style_custom_value(formattedValue, formatting, value) {
		let $element = $(`<span>${formattedValue}</span>`);

		if (formatting.bold) $element.css("font-weight", "bold");
		if (formatting.italic) $element.css("font-style", "italic");
		if (formatting.warn_if_negative && typeof value === "number" && value < 0)
			$element.addClass("text-danger");
		if (formatting.color) $element.css("color", formatting.color);

		return $element.wrap("<p></p>").parent().html();
	},

	_format_special_view: function (value, row, column, data, default_formatter) {
		const selectedView = frappe.query_report.get_filter_value("selected_view");

		if (selectedView === "Growth") {
			const growthPercent = data[column.fieldname];
			if (growthPercent === undefined) return "NA";
			if (growthPercent === "") return "";

			if (column.fieldname === "total") {
				value = $(`<span>${growthPercent}</span>`);
			} else {
				value = $(`<span>${(growthPercent >= 0 ? "+" : "") + growthPercent + "%"}</span>`);
				if (growthPercent < 0) {
					value = $(value).addClass("text-danger");
				} else {
					value = $(value).addClass("text-success");
				}
			}
			return $(value).wrap("<p></p>").parent().html();
		} else {
			const marginPercent = data[column.fieldname];
			if (marginPercent === undefined) return "NA";

			value = $(`<span>${marginPercent + "%"}</span>`);
			if (marginPercent < 0) value = $(value).addClass("text-danger");
			else value = $(value).addClass("text-success");
			return $(value).wrap("<p></p>").parent().html();
		}
	},

	_format_standard_report: function (value, row, column, data, default_formatter, filter) {
		if (data && column.fieldname == erpnext.financial_statements.name_field) {
			value = data.section_name || data.account_name || value;

			if (filter && filter?.text && filter?.type == "contains") {
				if (!value.toLowerCase().includes(filter.text)) {
					return value;
				}
			}

			if (data.account || data.accounts) {
				column.link_onclick =
					"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
			}
			column.is_tree = true;
		}

		value = default_formatter(value, row, column, data);

		if (data && !data.parent_account && !data.parent_section) {
			value = $(`<span>${value}</span>`);

			var $value = $(value).css("font-weight", "bold");
			if (data.warn_if_negative && data[column.fieldname] < 0) {
				$value.addClass("text-danger");
			}

			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
	open_general_ledger: function (data) {
		if (!data.account && !data.accounts) return;
		let filters = frappe.query_report.filters;

		let project = $.grep(filters, function (e) {
			return e.df.fieldname == "project";
		});

		let cost_center = $.grep(filters, function (e) {
			return e.df.fieldname == "cost_center";
		});

		frappe.route_options = {
			account: data.account || data.accounts,
			company: frappe.query_report.get_filter_value("company"),
			from_date: data.from_date || data.year_start_date,
			to_date: data.to_date || data.year_end_date,
			project: project && project.length > 0 ? project[0].get_value() : "",
			cost_center: cost_center && cost_center.length > 0 ? cost_center[0].get_value() : "",
		};

		filters.forEach((f) => {
			if (f.df.fieldtype == "MultiSelectList") {
				if (f.df.fieldname in frappe.route_options) return;
				let value = f.get_value();
				if (value && value.length > 0) {
					frappe.route_options[f.df.fieldname] = value;
				}
			}
		});

		let report = "General Ledger";

		if (["Payable", "Receivable"].includes(data.account_type)) {
			report = data.account_type == "Payable" ? "Accounts Payable" : "Accounts Receivable";
			frappe.route_options["party_account"] = data.account;
			frappe.route_options["report_date"] = data.year_end_date;
		}

		frappe.set_route("query-report", report);
	},
	tree: true,
	name_field: "account",
	parent_field: "parent_account",
	initial_depth: 3,
	onload: function (report) {
		// dropdown for links to other financial statements
		erpnext.financial_statements.filters = get_filters();

		let fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today());
		var filters = report.get_values();

		if (!filters.period_start_date || !filters.period_end_date) {
			frappe.model.with_doc("Fiscal Year", fiscal_year, function (r) {
				var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
				frappe.query_report.set_filter_value({
					period_start_date: fy.year_start_date,
					period_end_date: fy.year_end_date,
				});
			});
		}

		if (report.page) {
			const views_menu = report.page.add_custom_button_group(__("Financial Statements"));

			report.page.add_custom_menu_item(views_menu, __("Balance Sheet"), function () {
				var filters = report.get_values();
				frappe.set_route("query-report", "Balance Sheet", { company: filters.company });
			});

			report.page.add_custom_menu_item(views_menu, __("Profit and Loss"), function () {
				var filters = report.get_values();
				frappe.set_route("query-report", "Profit and Loss Statement", { company: filters.company });
			});

			report.page.add_custom_menu_item(views_menu, __("Cash Flow Statement"), function () {
				var filters = report.get_values();
				frappe.set_route("query-report", "Cash Flow", { company: filters.company });
			});
		}
	},
};

function get_filters() {
	let filters = [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Fiscal Year", "Date Range"],
			default: ["Fiscal Year"],
			reqd: 1,
			on_change: function () {
				let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");
				frappe.query_report.toggle_filter_display(
					"from_fiscal_year",
					filter_based_on === "Date Range"
				);
				frappe.query_report.toggle_filter_display("to_fiscal_year", filter_based_on === "Date Range");
				frappe.query_report.toggle_filter_display(
					"period_start_date",
					filter_based_on === "Fiscal Year"
				);
				frappe.query_report.toggle_filter_display(
					"period_end_date",
					filter_based_on === "Fiscal Year"
				);

				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "period_start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			mandatory_depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "period_end_date",
			label: __("End Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			mandatory_depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "from_fiscal_year",
			label: __("Start Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "to_fiscal_year",
			label: __("End Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{ value: "Monthly", label: __("Monthly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Half-Yearly", label: __("Half-Yearly") },
				{ value: "Yearly", label: __("Yearly") },
			],
			default: "Yearly",
			reqd: 1,
		},
		// Note:
		// If you are modifying this array such that the presentation_currency object
		// is no longer the last object, please make adjustments in cash_flow.js
		// accordingly.
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
			options: "Cost Center",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Project", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
			options: "Project",
		},
	];

	// Dynamically set 'default' values for fiscal year filters
	let fy_filters = filters.filter((x) => {
		return ["from_fiscal_year", "to_fiscal_year"].includes(x.fieldname);
	});
	let fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), false, false);
	if (fiscal_year) {
		fy_filters.forEach((x) => {
			x.default = fiscal_year;
		});
	}

	return filters;
}
