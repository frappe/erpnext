// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Financial Report Template", {
	refresh(frm) {
		// add custom button to view missed accounts
		frm.add_custom_button(__("View Account Coverage"), function () {
			let selected_rows = frm.get_field("rows").grid.get_selected_children();
			const has_selection = selected_rows.length > 0;
			if (selected_rows.length === 0) selected_rows = frm.doc.rows;

			show_accounts_tree(selected_rows, has_selection);
		});

		// add custom button to open the financial report
		frm.add_custom_button(__("View Report"), function () {
			frappe.set_route("query-report", frm.doc.report_type, {
				report_template: frm.doc.name,
			});
		});
	},

	validate(frm) {
		if (!frm.doc.rows || frm.doc.rows.length === 0) {
			frappe.msgprint(__("At least one row is required for a financial report template"));
		}
	},
});

frappe.ui.form.on("Financial Report Row", {
	data_source(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		update_formula_label(frm, row.data_source);
		update_formula_description(frm, row.data_source);

		if (row.data_source !== "Account Data") {
			frappe.model.set_value(cdt, cdn, "balance_type", "");
		}

		if (["Blank Line", "Column Break", "Section Break"].includes(row.data_source)) {
			frappe.model.set_value(cdt, cdn, "calculation_formula", "");
		}

		set_up_filters_editor(frm, cdt, cdn);
	},

	form_render(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		update_formula_label(frm, row.data_source);
		update_advanced_formula_property(frm, cdt, cdn);
		set_up_filters_editor(frm, cdt, cdn);
		update_formula_description(frm, row.data_source);
	},

	calculation_formula(frm, cdt, cdn) {
		update_advanced_formula_property(frm, cdt, cdn);
	},

	advanced_filtering(frm, cdt, cdn) {
		set_up_filters_editor(frm, cdt, cdn);
	},
});

// FILTERS EDITOR

function set_up_filters_editor(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (row.data_source !== "Account Data" || row.advanced_filtering) return;

	const grid_row = frm.fields_dict["rows"].grid.get_row(cdn);
	const wrapper = grid_row.get_field("filters_editor").$wrapper;
	wrapper.empty();

	const ACCOUNT = "Account";
	const FIELD_IDX = 1;
	const OPERATOR_IDX = 2;
	const VALUE_IDX = 3;

	// Parse saved filters
	let saved_filters = [];

	if (row.calculation_formula) {
		try {
			const parsed = JSON.parse(row.calculation_formula);

			if (Array.isArray(parsed)) saved_filters = [parsed];
			else if (parsed.and) saved_filters = parsed.and;
		} catch (e) {
			frappe.show_alert({
				message: __("Invalid filter formula. Please check the syntax."),
				indicator: "red",
			});
		}
	}

	if (saved_filters.length)
		// Ensure every filter starts with "Account"
		saved_filters = saved_filters.map((f) => [ACCOUNT, ...f]);

	frappe.model.with_doctype(ACCOUNT, () => {
		const filter_group = new frappe.ui.FilterGroup({
			parent: wrapper,
			doctype: ACCOUNT,
			on_change: () => {
				// only need [[field, operator, value]]
				const filters = filter_group
					.get_filters()
					.map((f) => [f[FIELD_IDX], f[OPERATOR_IDX], f[VALUE_IDX]]);

				const current = filters.length > 1 ? { and: filters } : filters[0];
				frappe.model.set_value(cdt, cdn, "calculation_formula", JSON.stringify(current));
			},
		});

		filter_group.add_filters_to_filter_group(saved_filters);
	});
}

function update_advanced_formula_property(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const is_advanced = is_advanced_formula(row);

	frm.set_df_property("rows", "read_only", is_advanced, frm.doc.name, "advanced_filtering", cdn);

	if (is_advanced && !row.advanced_filtering) {
		row.advanced_filtering = 1;
		frm.refresh_field("rows");
	}
}

function is_advanced_formula(row) {
	if (!row || row.data_source !== "Account Data") return false;

	let parsed = null;
	if (row.calculation_formula) {
		try {
			parsed = JSON.parse(row.calculation_formula);
		} catch (e) {
			console.warn("Invalid JSON in calculation_formula:", e);
			return false;
		}
	}

	if (Array.isArray(parsed)) return false;
	if (parsed?.or) return true;
	if (parsed?.and) return parsed.and.some((cond) => !Array.isArray(cond));

	return false;
}

// ACCOUNTS TREE VIEW

function show_accounts_tree(template_rows, has_selection) {
	// filtered rows
	const account_rows = template_rows.filter((row) => row.data_source === "Account Data");

	if (account_rows.length === 0) {
		frappe.show_alert(__("No <strong>Account Data</strong> row found"));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Accounts Missing from Report"),
		fields: [
			{
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				label: "Company",
				reqd: 1,
				default: frappe.defaults.get_user_default("Company"),
				onchange: () => {
					const company_field = dialog.get_field("company");
					if (!company_field.value || company_field.value === company_field.last_value) return;
					refresh_tree_view(dialog, account_rows);
				},
			},
			{
				fieldname: "view_type",
				fieldtype: "Select",
				options: ["Missing Accounts", "Filtered Accounts"],
				label: "View",
				default: has_selection ? "Filtered Accounts" : "Missing Accounts",
				reqd: 1,
				onchange: () => {
					dialog.set_title(
						dialog.get_value("view_type") === "Missing Accounts"
							? __("Accounts Missing from Report")
							: __("Accounts Included in Report")
					);

					refresh_tree_view(dialog, account_rows);
				},
			},
			{
				fieldname: "tip",
				fieldtype: "HTML",
				label: "Tip",
				options: `
					<div class="alert alert-success" role="alert">
							Tip: Select report lines to view their accounts
					</div>
				`,
				depends_on: has_selection ? "eval: false" : "eval: true",
			},
			{
				fieldname: "tree_area",
				fieldtype: "HTML",
				label: "Chart of Accounts",
				read_only: 1,
				depends_on: "eval: doc.company",
			},
		],
		primary_action_label: __("Done"),
		primary_action() {
			dialog.hide();
		},
	});

	dialog.show();
	refresh_tree_view(dialog, account_rows);
}

async function refresh_tree_view(dialog, account_rows) {
	const missed = dialog.get_value("view_type") === "Missing Accounts";
	const company = dialog.get_value("company");

	const wrapper = dialog.get_field("tree_area").$wrapper;
	wrapper.empty();

	// get filtered accounts
	const { message: filtered_accounts } = await frappe.call({
		method: "erpnext.accounts.doctype.financial_report_template.financial_report_engine.get_filtered_accounts",
		args: { company: company, account_rows: account_rows },
	});

	// render tree
	const tree = new FilteredTree({
		parent: wrapper,
		label: company,
		root_value: company,
		method: "erpnext.accounts.doctype.financial_report_template.financial_report_engine.get_children_accounts",
		args: { doctype: "Account", company: company, filtered_accounts: filtered_accounts, missed: missed },
		toolbar: [],
	});

	tree.load_children(tree.root_node, true);
}

class FilteredTree extends frappe.ui.Tree {
	render_children_of_all_nodes(data_list) {
		data_list = this.get_filtered_data_list(data_list);
		super.render_children_of_all_nodes(data_list);
	}

	get_filtered_data_list(data_list) {
		let removed_nodes = new Set();

		// Filter nodes with no data
		data_list = data_list.filter((d) => {
			if (d.data.length === 0) {
				removed_nodes.add(d.parent);
				return false;
			}
			return true;
		});

		// Remove references to removed nodes and iteratively remove empty parents
		while (removed_nodes.size > 0) {
			const current_removed = [...removed_nodes];
			removed_nodes.clear();

			data_list = data_list.filter((d) => {
				d.data = d.data.filter((a) => !current_removed.includes(a.value));

				if (d.data.length === 0) {
					removed_nodes.add(d.parent);
					return false;
				}
				return true;
			});
		}

		return data_list;
	}
}

function update_formula_label(frm, data_source) {
	const grid = frm.fields_dict.rows.grid;
	const field = grid.fields_map.calculation_formula;
	if (!field) return;

	const labels = {
		"Account Data": "Account Filter",
		"Custom API": "API Method Path",
	};

	grid.update_docfield_property(
		"calculation_formula",
		"label",
		labels[data_source] || "Calculation Formula"
	);
}

// FORMULA DESCRIPTION

function update_formula_description(frm, data_source) {
	if (!data_source) return;

	let grid = frm.fields_dict.rows.grid;
	let field = grid.fields_map.formula_description;
	if (!field) return;

	// Common CSS styles and elements
	const container_style = `style="padding: var(--padding-md); border: 1px solid var(--border-color); border-radius: var(--border-radius); margin-top: var(--margin-sm);"`;
	const title_style = `style="margin-top: 0; color: var(--text-color);"`;
	const subtitle_style = `style="color: var(--text-color); margin-bottom: var(--margin-xs);"`;
	const text_style = `style="margin-bottom: var(--margin-sm); color: var(--text-muted);"`;
	const list_style = `style="margin-bottom: var(--margin-sm); color: var(--text-muted); font-size: 0.9em;"`;
	const note_style = `style="margin-bottom: 0; color: var(--text-muted); font-size: 0.9em;"`;
	const tip_style = `style="margin-bottom: 0; color: var(--text-color); font-size: 0.85em;"`;

	let description_html = "";

	if (data_source === "Account Data") {
		description_html = `
			<div ${container_style}>
				<h5 ${title_style}>Account Filter Guide</h5>
				<p ${text_style}>Specify which accounts to include in this line.</p>

				<h6 ${subtitle_style}>Basic Examples:</h6>
				<ul ${list_style}>
					<li><code>["account_type", "=", "Cash"]</code> - All Cash accounts</li>
					<li><code>["root_type", "in", ["Asset", "Liability"]]</code> - All Asset and Liability accounts</li>
					<li><code>["account_category", "like", "Revenue"]</code> - Revenue accounts</li>
				</ul>

				<h6 ${subtitle_style}>Multiple Conditions (AND/OR):</h6>
				<ul ${list_style}>
					<li><code>{"and": [["root_type", "=", "Asset"], ["account_type", "=", "Cash"]]}</code></li>
					<li><code>{"or": [["account_category", "like", "Revenue"], ["account_category", "like", "Income"]]}</code></li>
				</ul>

				<p ${note_style}><strong>Available operators:</strong> <code>=, !=, in, not in, like, not like, is</code></p>
				<p ${tip_style}><strong>Multi-Company Tip:</strong> Use fields like <code>account_type</code>, <code>root_type</code>, and <code>account_category</code> for templates that work across multiple companies.</p>
			</div>`;
	} else if (data_source === "Calculated Amount") {
		description_html = `
			<div ${container_style}>
				<h5 ${title_style}>Formula Guide</h5>
				<p ${text_style}>Create calculations using reference codes from other lines.</p>

				<h6 ${subtitle_style}>Basic Examples:</h6>
				<ul ${list_style}>
					<li><code>REV100 + REV200</code> - Add two revenue lines</li>
					<li><code>ASSETS - LIABILITIES</code> - Calculate equity</li>
					<li><code>REVENUE * 0.1</code> - 10% of revenue</li>
				</ul>

				<h6 ${subtitle_style}>Common Functions:</h6>
				<ul ${list_style}>
					<li><code>abs(value)</code> - Remove negative sign</li>
					<li><code>round(value)</code> - Round to whole number</li>
					<li><code>max(val1, val2)</code> - Larger of two values</li>
					<li><code>min(val1, val2)</code> - Smaller of two values</li>
				</ul>

				<p ${note_style}><strong>Required:</strong> Use "Reference Code" from other rows in your formulas.</p>
			</div>`;
	} else if (data_source === "Custom API") {
		description_html = `
			<div ${container_style}>
				<h5 ${title_style}>Custom API Setup</h5>
				<p ${text_style}>Path to your custom method that returns financial data.</p>

				<h6 ${subtitle_style}>Format:</h6>
				<ul ${list_style}>
					<li><code>erpnext.custom.financial_apis.get_custom_revenue</code></li>
					<li><code>my_app.financial_reports.get_kpi_data</code></li>
				</ul>

				<h6 ${subtitle_style}>Return Format:</h6>
				<p ${text_style}>Numbers for each period: <code>[1000.0, 1200.0, 1150.0]</code></p>
			</div>`;
	} else if (data_source === "Blank Line") {
		description_html = `
			<div ${container_style}>
				<h5 ${title_style}>Blank Line</h5>
				<p ${text_style}>Adds empty space for better visual separation.</p>

				<h6 ${subtitle_style}>Use For:</h6>
				<ul ${list_style}>
					<li>Separating major sections</li>
					<li>Adding space before totals</li>
				</ul>

				<p ${note_style}><strong>Note:</strong> No formula needed - creates visual spacing only.</p>
			</div>`;
	} else if (data_source === "Column Break") {
		description_html = `
			<div ${container_style}>
				<h5 ${title_style}>Column Break</h5>
				<p ${text_style}>Creates a visual break for side-by-side layout.</p>

				<h6 ${subtitle_style}>Use For:</h6>
				<ul ${list_style}>
					<li>Horizontal P&L statements</li>
					<li>Side-by-side Balance Sheet sections</li>
				</ul>

				<p ${note_style}><strong>Note:</strong> No formula needed - this is for formatting only.</p>
			</div>`;
	} else if (data_source === "Section Break") {
		description_html = `
			<div ${container_style}>
				<h5 ${title_style}>Section Break</h5>
				<p ${text_style}>Creates a visual break for separating different sections.</p>

				<h6 ${subtitle_style}>Use For:</h6>
				<ul ${list_style}>
					<li>Separating major sections in a report - say trading & profit and loss</li>
					<li>Improving readability by adding space</li>
				</ul>

				<p ${note_style}><strong>Note:</strong> No formula needed - this is for formatting only.</p>
			</div>`;
	}

	grid.update_docfield_property("formula_description", "options", description_html);
}
