// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tax Withholding Category", {
	setup: function (frm) {
		frm.set_query("account", "accounts", function (doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			if (child.company) {
				return {
					filters: {
						company: child.company,
						root_type: ["in", ["Asset", "Liability"]],
						is_group: 0,
					},
				};
			}
		});
	},

	refresh: function (frm) {
		update_rates_read_only_state(frm);
	},

	disable_cumulative_threshold: function (frm) {
		toggle_threshold_settings(frm, "disable_cumulative_threshold");
		if (frm.doc.disable_cumulative_threshold) {
			reset_rates_column(frm, "cumulative_threshold");
		}
		update_rates_read_only_state(frm);
	},

	disable_transaction_threshold: function (frm) {
		toggle_threshold_settings(frm, "disable_transaction_threshold");
		if (frm.doc.disable_transaction_threshold) {
			reset_rates_column(frm, "single_threshold");
		}
		update_rates_read_only_state(frm);
	},
});

function toggle_threshold_settings(frm, field_name) {
	if (frm.doc[field_name]) {
		const other_field =
			field_name === "disable_cumulative_threshold"
				? "disable_transaction_threshold"
				: "disable_cumulative_threshold";
		frm.set_value(other_field, 0);
	}
}

function update_rates_read_only_state(frm) {
	frm.fields_dict["rates"].grid.update_docfield_property(
		"cumulative_threshold",
		"read_only",
		frm.doc.disable_cumulative_threshold
	);
	frm.fields_dict["rates"].grid.update_docfield_property(
		"single_threshold",
		"read_only",
		frm.doc.disable_transaction_threshold
	);
}

function reset_rates_column(frm, field_name) {
	$.each(frm.doc.rates || [], function (i, row) {
		row[field_name] = 0;
	});
	frm.refresh_field("rates");
}
