// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Process Asset Depreciation", {
	onload(frm) {
		if (!frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("company"));
		}
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}
	},

	refresh(frm) {
		frm.disable_save();

		const grid = frm.get_field("assets").grid;
		grid.cannot_add_rows = true;
		grid.df.cannot_delete_rows = true;

		frm.add_custom_button(__("Fetch Assets"), () => frm.trigger("fetch_assets"), null, "primary");
		frm.add_custom_button(__("Create Depreciation Entries"), () => frm.trigger("create_entries"));

		frm.custom_buttons[__("Create Depreciation Entries")].prop("disabled", true);
	},

	company: (frm) => frm.trigger("fetch_assets"),
	date: (frm) => frm.trigger("fetch_assets"),
	asset_category: (frm) => frm.trigger("fetch_assets"),
	finance_book: (frm) => frm.trigger("fetch_assets"),

	fetch_assets(frm) {
		if (!frm.doc.date) return;

		frappe.call({
			method: "erpnext.assets.doctype.process_asset_depreciation.process_asset_depreciation.get_pending_depreciation_assets",
			args: {
				date: frm.doc.date,
				company: frm.doc.company,
				asset_category: frm.doc.asset_category,
				finance_book: frm.doc.finance_book,
			},
			freeze: true,
			freeze_message: __("Fetching pending assets..."),
			callback(r) {
				frm.clear_table("assets");
				for (const row of r.message || []) {
					frm.add_child("assets", row);
				}
				frm.refresh_field("assets");
				frm.trigger("update_create_button");
			},
		});
	},

	update_create_button(frm) {
		const grid = frm.get_field("assets").grid;
		const selected = grid.get_selected_children() || [];
		const has_data = (frm.doc.assets || []).length > 0;
		const $btn = frm.custom_buttons[__("Create Depreciation Entries")];
		const $fetch = frm.custom_buttons[__("Fetch Assets")];

		if (!$btn) return;

		$btn.prop("disabled", !has_data).css({
			"background-color": has_data ? "#000" : "",
			"border-color": has_data ? "#000" : "",
			color: has_data ? "#fff" : "",
		});

		if ($fetch) {
			$fetch.toggleClass("btn-primary", !has_data).toggleClass("btn-default", has_data);
		}

		$btn.text(
			selected.length
				? __("Create Depreciation Entries ({0})", [selected.length])
				: __("Create Depreciation Entries")
		);
	},

	create_entries(frm) {
		const grid = frm.get_field("assets").grid;
		const selected = grid.get_selected_children() || [];
		const rows = selected.length ? selected : frm.doc.assets || [];

		if (!rows.length) {
			frappe.msgprint(__("No assets to process. Please fetch assets first."));
			return;
		}

		const names = rows.map((r) => r.depr_schedule_name);
		const label = selected.length
			? __("{0} selected asset(s)", [selected.length])
			: __("all {0} asset(s)", [rows.length]);

		frappe.confirm(
			__("Create depreciation journal entries for {0} up to {1}?", [
				`<strong>${label}</strong>`,
				`<strong>${frm.doc.date}</strong>`,
			]),
			() => {
				frappe.call({
					method: "erpnext.assets.doctype.process_asset_depreciation.process_asset_depreciation.create_depreciation_entries",
					args: { depr_schedule_names: names, date: frm.doc.date },
					freeze: true,
					freeze_message: __("Creating depreciation entries..."),
					callback(r) {
						const result = r.message || {};
						const success = (result.success || []).length;
						const failed = result.failed || [];

						if (failed.length) {
							const errors = failed.map((f) => `<li>${f.name}: ${f.error}</li>`).join("");
							frappe.msgprint({
								title: __("Partial Success"),
								message: __(
									"{0} entries created. {1} failed:<ul>{2}</ul>",
									[success, failed.length, errors]
								),
								indicator: "orange",
							});
						} else {
							frappe.show_alert({
								message: __("{0} depreciation entries created successfully.", [success]),
								indicator: "green",
							});
						}

						frm.trigger("fetch_assets");
					},
				});
			}
		);
	},
});
