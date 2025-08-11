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

		validate_formulas(frm);
	},
});

function validate_formulas(frm) {
	let row_codes = frm.doc.rows.map((r) => r.reference_code).filter(Boolean);

	frm.doc.rows.forEach((row, i) => {
		if (!row.calculation_formula) return;

		// balanced parentheses
		let open_count = (row.calculation_formula.match(/\(/g) || []).length;
		let close_count = (row.calculation_formula.match(/\)/g) || []).length;

		if (open_count !== close_count) {
			frappe.msgprint(__("Formula in row {0} has unbalanced parentheses", [i + 1]));
		}

		// referenced codes exist
		if (row.data_type !== "Formula/Calculation") return;
		row_codes.forEach((code) => {
			if (row.calculation_formula.includes(code) && !row_codes.includes(code)) {
				frappe.msgprint(__("Formula in row {0} references non-existent code: {1}", [i + 1, code]));
			}
		});
	});
}
