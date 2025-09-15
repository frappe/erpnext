// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Financial Report Template", {
	refresh(frm) {
		if (frm.doc.is_standard) {
			frm.dashboard.add_comment(
				__(
					"<strong>Warning:</strong> This template is system generated and may be overwritten by a future update. Duplicate it to customize."
				),
				"yellow",
				true
			);
		}

		// add custom button to view missed accounts
		if (!frm.is_new() && frm.doc.rows.length > 0) {
			frm.add_custom_button(__("View Missing Accounts"), function () {
				show_accounts_tree(frm.doc.rows, true);
			});
		}
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
		update_formula_description(frm, row.data_source);

		if (row.data_source !== "Account Data") {
			frappe.model.set_value(cdt, cdn, "balance_type", "");
		}

		// TODO: should  do it on server side?
		if (["Blank Line", "Column Break", "Section Break"].includes(row.data_source)) {
			frappe.model.set_value(cdt, cdn, "calculation_formula", "");
		}

		set_up_filters_editor(frm, cdt, cdn);
	},

	form_render(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		set_up_filters_editor(frm, cdt, cdn);
		update_formula_description(frm, row.data_source);
	},

	view_filtered_accounts(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		show_accounts_tree([row], false);
	},

	view_missing_accounts(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		show_accounts_tree([row], true);
	},

	advance_filtering(frm, cdt, cdn) {
		set_up_filters_editor(frm, cdt, cdn);
	},
});

function update_formula_description(frm, data_source) {
	if (!data_source) return;

	let grid = frm.fields_dict.rows.grid;
	let field = grid.fields_map.formula_description;
	if (!field) return;

	// Common CSS styles and elements
	const container_style = `style='padding: var(--padding-md); border: 1px solid var(--border-color); border-radius: var(--border-radius); margin-top: var(--margin-sm);'`;
	const title_style = `style='margin-top: 0; color: var(--text-color);'`;
	const subtitle_style = `style='color: var(--text-color); margin-bottom: var(--margin-xs);'`;
	const text_style = `style='margin-bottom: var(--margin-sm); color: var(--text-muted);'`;
	const list_style = `style='margin-bottom: var(--margin-sm); color: var(--text-muted); font-size: 0.9em;'`;
	const note_style = `style='margin-bottom: 0; color: var(--text-muted); font-size: 0.9em;'`;
	const tip_style = `style='margin-bottom: 0; color: var(--text-color); font-size: 0.85em;'`;

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

				<p ${note_style}><strong>Required:</strong> Use 'Reference Code' from other rows in your formulas.</p>
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

				<p ${note_style}><strong>Note:</strong> Method must be decorated with <code>@frappe.whitelist()</code></p>
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

function set_up_filters_editor(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (row.data_source !== "Account Data" || row.advance_filtering) {
		return;
	}

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

			if (Array.isArray(parsed)) {
				saved_filters = [parsed]; // array of array needed
			} else if (parsed.and) {
				saved_filters = parsed.and;
			}
		} catch (e) {
			console.warn("Invalid calculation_formula JSON:", e);
		}
	}

	// Ensure every filter starts with "Account"
	if (saved_filters.length) {
		saved_filters = saved_filters.map((f) => [ACCOUNT, ...f]);
	}

	frappe.model.with_doctype(ACCOUNT, () => {
		const filter_group = new frappe.ui.FilterGroup({
			parent: wrapper,
			doctype: ACCOUNT,
			on_change: () => {
				// only need [[field, operator, value]]
				const filters = filter_group
					.get_filters()
					.map((f) => [f[FIELD_IDX], f[OPERATOR_IDX], f[VALUE_IDX]]);

				update_account_filter_for_and_conditions(cdt, cdn, filters);
			},
		});

		try {
			filter_group.add_filters_to_filter_group(saved_filters);
		} catch (error) {
			frappe.show_alert({
				message: __("Failed to add filters to filter group: {0}", [error.message]),
				indicator: "red",
			});
		}
	});
}

function update_account_filter_for_and_conditions(cdt, cdn, filters) {
	const row = locals[cdt][cdn];

	let previous = {};

	// TODO: `or` conditions are not handled
	// TODO: default set {"and": []}
	if (row.account_filters) {
		try {
			previous = JSON.parse(row.account_filters);
		} catch {
			previous = {};
		}
	}

	// Always overwrite AND, preserve OR if present
	const current = { and: filters };

	if (typeof previous === "object" && previous.or) {
		current.or = previous.or;
	}

	frappe.model.set_value(cdt, cdn, "calculation_formula", JSON.stringify(current));
}

function show_accounts_tree(template_rows, missed = false) {
	// filtered rows
	const account_rows = template_rows.filter((row) => row.data_source === "Account Data");

	if (account_rows.length === 0) {
		frappe.show_alert(__("No <strong>Account Data</strong> row found"));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: missed ? __("Missing Accounts") : __("Filtered Accounts"),
		fields: [
			{
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				label: "Company",
				reqd: 1,
				onchange: function () {
					const company = dialog.get_value("company");

					if (!company) return;

					// render tree
					const wrapper = dialog.get_field("tree_area").$wrapper;
					wrapper.empty();

					new frappe.ui.Tree({
						parent: wrapper,
						label: company,
						root_value: company,
						method: "erpnext.accounts.doctype.financial_report_template.financial_report_engine.get_children_accounts",
						args: { company: company, account_rows: account_rows, missed: missed },
						toolbar: [],
					});
				},
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
}
