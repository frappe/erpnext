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
	},

	validate(frm) {
		if (!frm.doc.rows || frm.doc.rows.length === 0) {
			frappe.msgprint(__("At least one row is required for a financial report template"));
		}
	},
});

frappe.ui.form.on("Financial Report Row", {
	data_source(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		update_formula_description(frm, cdt, cdn, row.data_source);

		if (row.data_source !== "Account Data") {
			frappe.model.set_value(cdt, cdn, "balance_type", "");
		}

		if (["Blank Line", "Column Break"].includes(row.data_source)) {
			frappe.model.set_value(cdt, cdn, "calculation_formula", "");
		}
	},

	refresh(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		update_formula_description(frm, cdt, cdn, row.data_source);
	},
});

function update_formula_description(frm, cdt, cdn, data_source) {
	let grid = frm.fields_dict.rows.grid;
	let field = grid.fields_map.formula_description;
	console.log(field);
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

				<h6 ${subtitle_style}>Examples:</h6>
				<ul ${list_style}>
					<li><code>REV100 + REV200</code> - Add two revenue lines</li>
					<li><code>ASSETS - LIABILITIES</code> - Calculate equity</li>
					<li><code>(REV100 + REV200) * 0.1</code> - 10% of combined revenue</li>
					<li><code>GROSS_PROFIT / TOTAL_REVENUE</code> - Profit margin</li>
				</ul>

				<p ${note_style}><strong>Required:</strong> Use 'Line Reference' codes from other rows in your formulas.</p>
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
	}

	grid.update_docfield_property("formula_description", "options", description_html);
}
