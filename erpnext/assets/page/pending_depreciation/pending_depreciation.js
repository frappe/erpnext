// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.pages["pending-depreciation"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Pending Depreciation"),
		single_column: true,
	});

	new erpnext.assets.PendingDepreciation(page);
};

frappe.provide("erpnext.assets");

erpnext.assets.PendingDepreciation = class PendingDepreciation {
	constructor(page) {
		this.page = page;
		this.selected = new Set();
		this.data = [];
		this.make_filters();
		this.make_action_button();
		this.make_table_container();
	}

	make_filters() {
		this.company_filter = this.page.add_field({
			fieldtype: "Link",
			fieldname: "company",
			label: __("Company"),
			options: "Company",
			default: frappe.defaults.get_default("company"),
			change: () => this.refresh_table(),
		});

		this.date_filter = this.page.add_field({
			fieldtype: "Date",
			fieldname: "date",
			label: __("Up to Date"),
			default: frappe.datetime.get_today(),
			reqd: 1,
			change: () => this.refresh_table(),
		});

		this.asset_category_filter = this.page.add_field({
			fieldtype: "Link",
			fieldname: "asset_category",
			label: __("Asset Category"),
			options: "Asset Category",
			change: () => this.refresh_table(),
		});

		this.finance_book_filter = this.page.add_field({
			fieldtype: "Link",
			fieldname: "finance_book",
			label: __("Finance Book"),
			options: "Finance Book",
			change: () => this.refresh_table(),
		});

		this.$fetch_btn = this.page.add_inner_button(
			__("Fetch Assets"),
			() => this.refresh_table(),
			null,
			"primary"
		);
	}

	make_action_button() {
		this.$create_btn = this.page
			.add_inner_button(__("Create Depreciation Entries"), () => this.create_entries())
			.prop("disabled", true);
	}

	make_table_container() {
		this.$wrapper = $(`<div class="pending-depreciation-table" style="margin-top:16px;"></div>`).appendTo(
			$(this.page.body)
		);
	}

	get_filters() {
		return {
			date: this.date_filter.get_value(),
			company: this.company_filter.get_value(),
			asset_category: this.asset_category_filter.get_value(),
			finance_book: this.finance_book_filter.get_value(),
		};
	}

	refresh_table() {
		const filters = this.get_filters();
		if (!filters.date) {
			frappe.msgprint(__("Please select an Up to Date."));
			return;
		}

		frappe.call({
			method: "erpnext.assets.page.pending_depreciation.pending_depreciation.get_pending_depreciation_assets",
			args: filters,
			freeze: true,
			freeze_message: __("Fetching pending assets..."),
			callback: (r) => {
				this.data = r.message || [];
				this.selected.clear();
				this.render_table();
			},
		});
	}

	render_table() {
		this.$wrapper.empty();

		if (!this.data.length) {
			this.$wrapper.html(
				`<div class="text-muted text-center" style="padding:40px 0;">${__("No pending depreciation entries found.")}</div>`
			);
			this.update_action_button();
			return;
		}

		const currency = frappe.boot.sysdefaults.currency;

		const $table = $(`
			<div class="table-responsive">
				<table class="table table-bordered table-hover" style="font-size:13px;">
					<thead>
						<tr>
							<th style="width:36px;">
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

		const $tbody = $table.find("tbody");

		this.data.forEach((row) => {
			const amount = format_currency(row.pending_depreciation_amount, currency);
			const $tr = $(`
				<tr data-schedule="${row.depr_schedule_name}">
					<td><input type="checkbox" class="row-select"></td>
					<td><a href="/app/asset/${row.asset}" target="_blank">${row.asset}</a></td>
					<td>${row.asset_name}</td>
					<td>${row.asset_category}</td>
					<td>${row.finance_book || ""}</td>
					<td>${__(row.depreciation_method)}</td>
					<td>${frappe.datetime.str_to_user(row.next_depreciation_date)}</td>
					<td class="text-right">${amount}</td>
				</tr>
			`);

			$tr.find(".row-select").on("change", (e) => {
				if (e.target.checked) {
					this.selected.add(row.depr_schedule_name);
				} else {
					this.selected.delete(row.depr_schedule_name);
					$table.find(".select-all").prop("checked", false);
				}
				this.update_action_button();
			});

			$tbody.append($tr);
		});

		$table.find(".select-all").on("change", (e) => {
			const checked = e.target.checked;
			this.data.forEach((row) => {
				if (checked) {
					this.selected.add(row.depr_schedule_name);
				} else {
					this.selected.delete(row.depr_schedule_name);
				}
			});
			$table.find(".row-select").prop("checked", checked);
			this.update_action_button();
		});

		this.$wrapper.append($table);

		const summary = __(
			"{0} asset(s) with pending depreciation found.",
			[`<strong>${this.data.length}</strong>`]
		);
		this.$wrapper.prepend(
			`<p class="text-muted" style="margin-bottom:8px;">${summary}</p>`
		);

		this.update_action_button();
	}

	update_action_button() {
		const has_selection = this.selected.size > 0;
		this.$create_btn
			.prop("disabled", !has_selection)
			.css({
				"background-color": has_selection ? "#000" : "",
				"border-color": has_selection ? "#000" : "",
				color: has_selection ? "#fff" : "",
			});
		this.$fetch_btn.css({
			"background-color": "",
			"border-color": "",
			color: "",
		});

		this.$create_btn.text(
			has_selection
				? __("Create Depreciation Entries ({0})", [this.selected.size])
				: __("Create Depreciation Entries")
		);
	}

	create_entries() {
		if (!this.selected.size) return;

		const filters = this.get_filters();
		const names = Array.from(this.selected);

		frappe.confirm(
			__(
				"Create depreciation journal entries for {0} selected asset(s) up to {1}?",
				[`<strong>${names.length}</strong>`, `<strong>${filters.date}</strong>`]
			),
			() => {
				frappe.call({
					method: "erpnext.assets.page.pending_depreciation.pending_depreciation.create_depreciation_entries",
					args: {
						depr_schedule_names: names,
						date: filters.date,
					},
					freeze: true,
					freeze_message: __("Creating depreciation entries..."),
					callback: (r) => {
						const result = r.message || {};
						const success = (result.success || []).length;
						const failed = result.failed || [];

						if (failed.length) {
							const errors = failed
								.map((f) => `<li>${f.name}: ${f.error}</li>`)
								.join("");
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

						this.refresh_table();
					},
				});
			}
		);
	}
};
