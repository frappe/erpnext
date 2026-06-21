// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("FTA Audit File", {
	refresh: function (frm) {
		// Generate FAF — available from Draft (first generation) and Error
		// (retry after a previous attempt failed). Queued/Generating are
		// blocked by the server guard; Generated/Submitted are intentionally
		// not re-generable.
		if (!frm.is_new() && ["Draft", "Error"].includes(frm.doc.status)) {
			frm.add_custom_button(
				__(frm.doc.status === "Error" ? "Retry FAF Generation" : "Generate FAF"),
				function () {
					frm.trigger("generate_faf");
				},
				__("Actions")
			);
		}

		// Add Mark as Submitted button for Generated status
		if (frm.doc.status === "Generated") {
			frm.add_custom_button(
				__("Mark as Submitted"),
				function () {
					frm.trigger("mark_submitted");
				},
				__("Actions")
			);
		}

		// Add Download button if file exists
		if (frm.doc.faf_file) {
			frm.add_custom_button(
				__("Download FAF"),
				function () {
					window.open(frm.doc.faf_file);
				},
				__("Actions")
			);
		}

		// Show status indicator
		frm.trigger("set_status_indicator");
	},

	generate_faf: function (frm) {
		frappe.confirm(
			__("This will generate the FTA Audit File for the selected period. Continue?"),
			function () {
				frm.call({
					doc: frm.doc,
					method: "generate_faf",
					freeze: true,
					freeze_message: __("Queuing FTA Audit File generation..."),
				}).then((r) => {
					if (!r.message) return;
					if (r.message.success) {
						frappe.show_alert({
							message: r.message.message,
							indicator: "green",
						});
					} else {
						frappe.msgprint({
							title: __("Generation Failed"),
							message: r.message.message,
							indicator: "red",
						});
					}
					frm.reload_doc();
				});
			}
		);
	},

	mark_submitted: function (frm) {
		frappe.confirm(
			__("Mark this FAF as submitted to FTA? This action is for record-keeping only."),
			function () {
				frm.call({
					doc: frm.doc,
					method: "mark_as_submitted",
				}).then((r) => {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: r.message.message,
							indicator: "green",
						});
						frm.reload_doc();
					}
				});
			}
		);
	},

	set_status_indicator: function (frm) {
		const status_colors = {
			Draft: "orange",
			Queued: "yellow",
			Generating: "blue",
			Generated: "green",
			Submitted: "blue",
			Error: "red",
		};

		if (frm.doc.status) {
			frm.page.set_indicator(__(frm.doc.status), status_colors[frm.doc.status] || "gray");
		}
	},

	from_date: function (frm) {
		frm.trigger("validate_dates");
	},

	to_date: function (frm) {
		frm.trigger("validate_dates");
	},

	validate_dates: function (frm) {
		if (frm.doc.from_date && frm.doc.to_date) {
			if (frm.doc.from_date > frm.doc.to_date) {
				frappe.msgprint(__("From Date cannot be after To Date"));
				frm.set_value("to_date", null);
			}
		}
	},
});
