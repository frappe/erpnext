// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Quality Inspection Reading Bundle", {
	refresh(frm) {
		frm.trigger("toggle_populate_button");
	},

	quality_inspection_template(frm) {
		frm.trigger("toggle_populate_button");
	},

	quantity(frm) {
		frm.trigger("toggle_populate_button");
	},

	toggle_populate_button(frm) {
		frm.remove_custom_button(__("Populate Units"));
		if (frm.doc.quality_inspection_template && frm.doc.quantity > 0) {
			frm.add_custom_button(__("Populate Units"), () => {
				frm.call("populate_units").then(() => {
					frm.refresh_field("entries");
					frm.dirty();
				});
			});
		}
	},
});

// Live evaluation while readings are typed; the server re-derives on save.
frappe.ui.form.on("Quality Inspection Reading Entry", {
	reading_value(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const reading = (row.reading_value || "").trim();
		if (!reading) {
			return; // no reading yet: the chosen status stands
		}

		let status;
		if (cint(row.numeric)) {
			const value = parseFloat(reading);
			status = value >= flt(row.min_value) && value <= flt(row.max_value) ? "Accepted" : "Rejected";
		} else if ((row.value || "").trim()) {
			status = reading.toLowerCase() === row.value.trim().toLowerCase() ? "Accepted" : "Rejected";
		} else {
			return; // no acceptance criteria: manual judgement
		}

		if (row.status !== status) {
			frappe.model.set_value(cdt, cdn, "status", status);
		}
		roll_up_unit_counts(frm);
	},

	status(frm) {
		roll_up_unit_counts(frm);
	},
});

function roll_up_unit_counts(frm) {
	const rejected_units = new Set();
	const inspected_units = new Set();
	for (const entry of frm.doc.entries || []) {
		inspected_units.add(entry.unit_no);
		if (entry.status === "Rejected") {
			rejected_units.add(entry.unit_no);
		}
	}
	frm.set_value("rejected_qty", rejected_units.size);
	frm.set_value("accepted_qty", inspected_units.size - rejected_units.size);
}
