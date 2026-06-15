// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pending Depreciation Tool", {
	setup(frm) {
		frm._selected = new Set();
		frm._data = [];
	},

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

		frm.add_custom_button(__("Fetch Assets"), () => frm.trigger("fetch_assets"), null, "primary");
		frm.add_custom_button(__("Create Depreciation Entries"), () => frm.trigger("create_entries"));

		frm.trigger("update_create_button");
		frm.trigger("render_table");
	},

	company: (frm) => frm.trigger("fetch_assets"),
	date: (frm) => frm.trigger("fetch_assets"),
	asset_category: (frm) => frm.trigger("fetch_assets"),
	finance_book: (frm) => frm.trigger("fetch_assets"),

	fetch_assets(frm) {
		if (!frm.doc.date) {
			frm.get_field("pending_assets").$wrapper.html(
				`<div class="text-muted text-center" style="padding: 40px 0;">${__("Please select an Up to Date.")}</div>`
			);
			return;
		}

		frappe.call({
			method: "erpnext.assets.doctype.pending_depreciation_tool.pending_depreciation_tool.get_pending_depreciation_assets",
			args: {
				date: frm.doc.date,
				company: frm.doc.company,
				asset_category: frm.doc.asset_category,
				finance_book: frm.doc.finance_book,
			},
			freeze: true,
			freeze_message: __("Fetching pending assets..."),
			callback(r) {
				frm._data = r.message || [];
				frm._selected = new Set();
				frm.trigger("render_table");
			},
		});
	},

	render_table(frm) {
		const $wrapper = frm.get_field("pending_assets").$wrapper.empty();
		frm.trigger("update_create_button");

		if (!frm._data || !frm._data.length) {
			if (frm.doc.date) {
				$wrapper.html(
					`<div class="text-muted text-center" style="padding: 40px 0;">${__("No pending depreciation entries found.")}</div>`
				);
			}
			return;
		}

		const currency = frappe.boot.sysdefaults.currency;

		const $container = $(`
			<div class="table-responsive">
				<p class="text-muted" style="margin-bottom: 8px;">
					${__("{0} asset(s) with pending depreciation found.", [`<strong>${frm._data.length}</strong>`])}
				</p>
				<table class="table table-bordered table-hover" style="font-size: 13px;">
					<thead>
						<tr>
							<th style="width: 36px;">
								<input type="checkbox" class="select-all" title="${__("Select All")}">
							</th>
							<th>${__("Asset")}</th>
							<th>${__("Asset Name")}</th>
							<th>${__("Asset Category")}</th>
							<th>${__("Finance Book")}</th>
							<th>${__("Depreciation Method")}</th>
							<th>${__("Next Depreciation Date")}</th>
							<th class="text-right">${__("Pending Amount")}</th>
						</tr>
					</thead>
					<tbody></tbody>
				</table>
			</div>
		`);

		const $tbody = $container.find("tbody");

		frm._data.forEach((row) => {
			const $tr = $(`
				<tr>
					<td><input type="checkbox" class="row-select"></td>
					<td><a href="/app/asset/${row.asset}" target="_blank">${row.asset}</a></td>
					<td>${row.asset_name}</td>
					<td>${row.asset_category}</td>
					<td>${row.finance_book || ""}</td>
					<td>${__(row.depreciation_method)}</td>
					<td>${frappe.datetime.str_to_user(row.next_depreciation_date)}</td>
					<td class="text-right">${format_currency(row.pending_depreciation_amount, currency)}</td>
				</tr>
			`);

			$tr.find(".row-select").on("change", (e) => {
				e.target.checked
					? frm._selected.add(row.depr_schedule_name)
					: frm._selected.delete(row.depr_schedule_name);
				if (!e.target.checked) $container.find(".select-all").prop("checked", false);
				frm.trigger("update_create_button");
			});

			$tbody.append($tr);
		});

		$container.find(".select-all").on("change", (e) => {
			const checked = e.target.checked;
			frm._data.forEach((row) =>
				checked ? frm._selected.add(row.depr_schedule_name) : frm._selected.delete(row.depr_schedule_name)
			);
			$container.find(".row-select").prop("checked", checked);
			frm.trigger("update_create_button");
		});

		$wrapper.append($container);
	},

	update_create_button(frm) {
		const has_selection = frm._selected && frm._selected.size > 0;
		const $create = frm.custom_buttons[__("Create Depreciation Entries")];
		const $fetch = frm.custom_buttons[__("Fetch Assets")];

		if (!$create) return;

		$create.prop("disabled", !has_selection).css({
			"background-color": has_selection ? "#000" : "",
			"border-color": has_selection ? "#000" : "",
			color: has_selection ? "#fff" : "",
		});

		if ($fetch) {
			$fetch
				.toggleClass("btn-primary", !has_selection)
				.toggleClass("btn-default", has_selection);
		}

		$create.text(
			has_selection
				? __("Create Depreciation Entries ({0})", [frm._selected.size])
				: __("Create Depreciation Entries")
		);
	},

	create_entries(frm) {
		if (!frm._selected || !frm._selected.size) return;

		const names = Array.from(frm._selected);

		frappe.confirm(
			__(
				"Create depreciation journal entries for {0} selected asset(s) up to {1}?",
				[`<strong>${names.length}</strong>`, `<strong>${frm.doc.date}</strong>`]
			),
			() => {
				frappe.call({
					method: "erpnext.assets.doctype.pending_depreciation_tool.pending_depreciation_tool.create_depreciation_entries",
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
