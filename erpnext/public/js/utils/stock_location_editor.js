frappe.provide("erpnext.stock");

erpnext.stock.StockLocationEditor = class StockLocationEditor {
	constructor({ frm, cdt, cdn, wrapper, is_rejected }) {
		this.frm = frm;
		this.cdt = cdt;
		this.cdn = cdn;
		this.wrapper = $(wrapper);
		this.is_rejected = cint(is_rejected);
		this.config = erpnext.stock.get_sbie_config(frm.doc.doctype, cdt) || {};
		this.qty_field = this.is_rejected ? "rejected_qty" : this.config.qty_field || "qty";
		this.start = 0;
		this.page_length = 10;
		this.total_count = 0;
		this.server_total_count = 0;
		this.server_total_qty = 0;
		this.last_entries = [];
		this.make();
	}

	get row() {
		return locals[this.cdt][this.cdn];
	}

	get warehouse() {
		return erpnext.stock.get_sbie_warehouse(this.row, this.is_rejected);
	}

	get pending_key() {
		return `${this.cdn}::${this.is_rejected}`;
	}

	get pending() {
		let store = erpnext.stock.get_sbie_pending_map(this.frm);
		if (!store[this.pending_key]) {
			store[this.pending_key] = { new_entries: [], updates: {}, deleted: [] };
		}
		return store[this.pending_key];
	}

	has_pending() {
		let p = this.pending;
		return Boolean(
			p.delete_all || p.new_entries.length || p.deleted.length || Object.keys(p.updates).length
		);
	}

	clear_pending() {
		delete erpnext.stock.get_sbie_pending_map(this.frm)[this.pending_key];
	}

	toggle_section(show) {
		this.wrapper.closest(".form-section").toggle(show);
	}

	async make() {
		if (!this.row.item_code) {
			this.wrapper.empty();
			this.toggle_section(false);
			return;
		}

		this.item = await erpnext.stock.get_sbie_item_flags(this.row.item_code);
		this.show_rack_bin = await erpnext.stock.is_rack_and_bin_enabled();
		this.has_serial_batch = Boolean(cint(this.item.has_serial_no) || cint(this.item.has_batch_no));

		let hide =
			(!this.has_serial_batch && !this.show_rack_bin) ||
			(this.has_serial_batch && cint(this.row.use_serial_batch_fields));

		if (hide) {
			this.wrapper.empty();
			this.toggle_section(false);
			return;
		}

		this.toggle_section(true);
		this.render_skeleton();
		this.load_page();
	}

	inject_styles() {
		if ($("#serial-batch-inline-editor-styles").length) return;

		$(`<style id="serial-batch-inline-editor-styles">
				.serial-batch-inline-editor input::placeholder {
					text-align: left;
				}
				.serial-batch-inline-editor .sbie-table {
					overflow-x: auto;
					border: 1px solid var(--table-border-color);
					border-radius: var(--radius-md);
					background-color: var(--subtle-accent);
				}
				.serial-batch-inline-editor .sbie-table table {
					width: 100%;
					margin: 0;
					table-layout: fixed;
					border-collapse: separate;
					border-spacing: 0;
					font-size: var(--text-sm);
				}
				.serial-batch-inline-editor .sbie-table thead th {
					background-color: var(--subtle-fg);
					color: var(--gray-600);
					font-weight: var(--weight-regular);
					height: 32px;
					padding: 4px 8px;
					border-bottom: 1px solid var(--table-border-color);
					border-right: 1px solid var(--table-border-color);
					text-align: left;
				}
				.serial-batch-inline-editor .sbie-table thead th:first-child {
					border-top-left-radius: var(--radius-md);
				}
				.serial-batch-inline-editor .sbie-table thead th:last-child {
					border-top-right-radius: var(--radius-md);
					border-right: none;
				}
				.serial-batch-inline-editor .sbie-table tbody td {
					background-color: var(--fg-color);
					color: var(--text-muted);
					padding: var(--grid-padding);
					border-bottom: 1px solid var(--table-border-color);
					border-right: 1px solid var(--table-border-color);
					vertical-align: middle;
				}
				.serial-batch-inline-editor .sbie-table .sbie-qty-input {
					background-color: var(--fg-color);
					border: none;
					box-shadow: none;
					outline: none;
				}
				.serial-batch-inline-editor .sbie-table td.sbie-input-cell,
				.serial-batch-inline-editor .sbie-table tbody tr:not(.sbie-empty):hover td.sbie-input-cell {
					padding: 0;
					background-color: var(--fg-color);
				}
				.serial-batch-inline-editor .sbie-table td.sbie-input-cell .frappe-control,
				.serial-batch-inline-editor .sbie-table td.sbie-input-cell .form-group,
				.serial-batch-inline-editor .sbie-table td.sbie-input-cell .control-input {
					margin: 0;
				}
				.serial-batch-inline-editor .sbie-table td.sbie-input-cell input {
					width: 100%;
					height: 38px;
					border: none;
					border-radius: 0;
					box-shadow: none;
					outline: none;
					background-color: var(--fg-color);
					padding: 0 8px;
				}
				.serial-batch-inline-editor .sbie-table input.form-control {
					background-color: var(--fg-color);
				}
				.serial-batch-inline-editor .sbie-table .link-btn {
					background-color: var(--fg-color);
				}
				.serial-batch-inline-editor .sbie-table input[type="checkbox"] {
					margin: 0;
					vertical-align: middle;
				}
				.serial-batch-inline-editor .sbie-table tbody td:last-child {
					border-right: none;
				}
				.serial-batch-inline-editor .sbie-table tbody tr:last-child td {
					border-bottom: none;
				}
				.serial-batch-inline-editor .sbie-table tbody tr:last-child td:first-child {
					border-bottom-left-radius: var(--radius-md);
				}
				.serial-batch-inline-editor .sbie-table tbody tr:last-child td:last-child {
					border-bottom-right-radius: var(--radius-md);
				}
				.serial-batch-inline-editor .sbie-table tbody tr:not(.sbie-empty):hover td {
					background-color: var(--subtle-fg);
				}
				.serial-batch-inline-editor .sbie-table tbody tr.sbie-empty td {
					background-color: var(--subtle-accent);
				}
			</style>`).appendTo("head");
	}

	esc(value) {
		return frappe.utils.escape_html(cstr(value));
	}

	render_skeleton() {
		this.inject_styles();
		this.wrapper.html(`
			<div class="serial-batch-inline-editor">
				<div class="sbie-table"></div>
				<div class="sbie-footer" style="display: flex; gap: 8px; align-items: center; margin-top: 10px; flex-wrap: wrap;">
					<div style="flex: 1; display: flex; gap: 8px; align-items: center;">
						<button class="btn btn-sm btn-default sbie-add-row"
							style="height: 28px; padding: 2px 12px; white-space: nowrap;">${__("Add row")}</button>
						<button class="btn btn-sm btn-danger sbie-delete hidden"
							style="height: 28px; padding: 2px 10px; white-space: nowrap;">${__("Delete row")}</button>
					</div>
					<div class="sbie-pagination hidden" style="display: flex; gap: 4px; align-items: center;">
						<button class="btn btn-sm btn-default sbie-first-page" title="${__("First")}"
							style="height: 28px; padding: 2px 8px;">${frappe.utils.icon("chevron-first")}</button>
						<button class="btn btn-sm btn-default sbie-prev" style="height: 28px; padding: 2px 8px;">
							${frappe.utils.icon("chevron-left")}</button>
						<input class="sbie-page-number" type="text"
							style="width: 24px; height: 28px; text-align: center; border: none; outline: none;
								background: transparent; padding: 0;">
						<span class="text-muted small">${__("of")}</span>
						<span class="sbie-total-pages text-muted small"></span>
						<button class="btn btn-sm btn-default sbie-next" style="height: 28px; padding: 2px 8px;">
							${frappe.utils.icon("chevron-right")}</button>
						<button class="btn btn-sm btn-default sbie-last-page" title="${__("Last")}"
							style="height: 28px; padding: 2px 8px;">${frappe.utils.icon("chevron-last")}</button>
					</div>
					<div style="flex: 1; display: flex; gap: 8px; align-items: center; justify-content: flex-end;">
					<div class="sbie-summary text-muted small"></div>
					${this.has_serial_batch ? this.get_menu_html() : ""}
					</div>
				</div>
			</div>
		`);
		this.bind_events();
	}

	get_menu_html() {
		return `<div class="dropdown" style="display: inline-block;">
			<button type="button" class="btn btn-sm btn-default sbie-menu" data-toggle="dropdown"
				aria-expanded="false" style="height: 28px; padding: 2px 8px;">
				${frappe.utils.icon("ellipsis", "sm")}
			</button>
			<div class="dropdown-menu dropdown-menu-right">
				${
					this.get_type_of_transaction() === "Outward"
						? `<a class="dropdown-item sbie-auto-fetch-action">${
								cint(this.item.has_serial_no)
									? __("Auto Fetch Serial Nos")
									: __("Auto Fetch Batch Nos")
						  }</a>`
						: ""
				}
				<a class="dropdown-item sbie-scan-action">${
					cint(this.item.has_serial_no) ? __("Scan Serial Nos") : __("Scan Batch Nos")
				}</a>
				${
					cint(this.item.has_serial_no)
						? `<a class="dropdown-item sbie-range-action">${__(
								"Create Serial Nos from Range"
						  )}</a>`
						: ""
				}
				<a class="dropdown-item sbie-download-csv">${__("Download")}</a>
				<a class="dropdown-item sbie-upload-csv">${__("Upload")}</a>
			</div>
		</div>`;
	}

	get_csv_columns() {
		if (cint(this.item.has_serial_no) && cint(this.item.has_batch_no)) {
			return ["Serial No", "Batch No", "Quantity"];
		}

		if (cint(this.item.has_batch_no)) {
			return ["Batch No", "Quantity"];
		}

		return ["Serial No"];
	}

	download_csv() {
		let url;
		if (this.server_total_count) {
			let params = new URLSearchParams({
				voucher_type: this.frm.doc.doctype,
				voucher_no: this.frm.doc.name,
				voucher_detail_no: this.row.name,
				warehouse: this.warehouse,
			});
			url = `/api/method/erpnext.stock.serial_batch_inline_editor.download_ledger_entries_csv?${params}`;
		} else {
			url = `/api/method/erpnext.stock.serial_batch_bundle.download_blank_csv_template?content=${encodeURIComponent(
				JSON.stringify(this.get_csv_columns())
			)}`;
		}

		const w = window.open(frappe.urllib.get_full_url(url));
		if (!w) {
			frappe.msgprint(__("Please enable pop-ups"));
		}
	}

	upload_csv() {
		new frappe.ui.FileUploader({
			allow_multiple: false,
			restrictions: { allowed_file_types: [".csv"] },
			on_success: (file) => this.import_csv_file(file.file_url),
		});
	}

	async import_csv_file(file_url) {
		let data = await this.call("erpnext.stock.serial_batch_bundle.upload_csv_file", {
			item_code: this.row.item_code,
			file_path: file_url,
		});

		let entries = [];
		if (data.serial_nos && data.serial_nos.length) {
			entries = data.serial_nos;
		} else if (data.batch_nos && data.batch_nos.length) {
			entries = data.batch_nos;
		}

		if (!entries.length) {
			frappe.msgprint(__("No entries found in the uploaded file"));
			return;
		}

		if (this.server_total_count || this.has_pending()) {
			frappe.confirm(__("This will replace the existing entries. Continue?"), () =>
				this.replace_entries(entries)
			);
		} else {
			this.replace_entries(entries);
		}
	}

	async replace_entries(entries) {
		this.clear_pending();
		await this.upsert({ entries, replace: 1 });
		if (this.frm.is_dirty()) {
			this.frm.save();
		}
	}

	async add_new_row() {
		if (!this.warehouse) {
			frappe.msgprint(
				this.is_rejected
					? __("Please set Rejected Warehouse first")
					: __("Please set Warehouse first")
			);
			return;
		}

		let $pending = this.wrapper.find(".sbie-new-row");
		if ($pending.length) {
			this.commit_new_row($pending);
			if (this.wrapper.find(".sbie-new-row").length) {
				this.wrapper.find(".sbie-new-row input").first().focus();
				return;
			}
		}

		let $tbody = this.wrapper.find(".sbie-table tbody");
		if (!$tbody.length) return;

		this.wrapper.find(".sbie-empty").remove();
		this.wrapper.find(".sbie-table").css("overflow", "visible");
		let $tr = $(this.get_new_row_html()).appendTo($tbody);
		this.make_new_row_controls($tr);
	}

	get_new_row_html() {
		let show_serial = cint(this.item.has_serial_no);
		let show_batch = cint(this.item.has_batch_no);
		let qty_cell = show_serial
			? this.format_float(1)
			: `<input type="text" class="sbie-new-qty" data-fieldtype="Float"
				value="${this.format_float(1)}" style="text-align: right;">`;

		return `<tr class="sbie-new-row">
			<td style="text-align: center;"><input type="checkbox" class="sbie-check sbie-new-check"></td>
			<td style="text-align: center;">${this.get_effective_count() + 1}</td>
			${show_serial ? `<td class="sbie-new-serial sbie-input-cell"></td>` : ""}
			${show_batch ? `<td class="sbie-new-batch sbie-input-cell"></td>` : ""}
			${
				this.show_rack_bin
					? `<td class="sbie-new-rack sbie-input-cell"></td>
						<td class="sbie-new-bin sbie-input-cell"></td>`
					: ""
			}
			<td class="${show_serial ? "" : "sbie-input-cell"}" style="text-align: right;">${qty_cell}</td>
		</tr>`;
	}

	make_new_row_controls($tr) {
		this.new_serial_control = this.make_row_link_control($tr.find(".sbie-new-serial"), {
			options: "Serial No",
			fieldname: "sbie_new_serial",
			placeholder: __("Scan / select Serial No"),
			get_query: () => ({ filters: { item_code: this.row.item_code } }),
			onchange: () => this.on_new_serial_change($tr),
		});

		this.new_batch_control = this.make_row_link_control($tr.find(".sbie-new-batch"), {
			options: "Batch",
			fieldname: "sbie_new_batch",
			placeholder: __("Select Batch No"),
			get_query: () => ({ filters: { item: this.row.item_code, disabled: 0 } }),
			onchange: () => this.on_new_batch_change($tr),
		});

		this.new_rack_control = this.make_row_link_control($tr.find(".sbie-new-rack"), {
			options: "Rack",
			fieldname: "sbie_new_rack",
			placeholder: __("Select Rack"),
			get_query: () => ({ filters: { disabled: 0 } }),
			onchange: () => this.on_new_rack_change($tr),
		});

		this.new_bin_control = this.make_row_link_control($tr.find(".sbie-new-bin"), {
			options: "Bin",
			fieldname: "sbie_new_bin",
			placeholder: __("Select Bin"),
			get_query: () => ({ filters: this.get_bin_filters() }),
			onchange: () => this.on_new_bin_change($tr),
		});

		$tr.find(".sbie-new-check")
			.on("mousedown", () => $tr.data("cancelled", 1))
			.on("change", (e) => {
				$tr.data("cancelled", e.target.checked ? 1 : 0);
				this.toggle_delete_button();
			});
		$tr.find("input").on("keydown", (e) => {
			if (e.which === 13) this.commit_new_row($tr);
		});
		$tr.find(".sbie-new-qty")
			.on("input", (e) => this.restrict_to_numeric(e))
			.on("focus", (e) => e.target.select())
			.on("change", () => this.commit_new_row($tr))
			.on("blur", () => this.commit_new_row($tr));

		let first_control = this.new_serial_control || this.new_batch_control || this.new_rack_control;
		first_control && first_control.$wrapper.find("input").focus();
	}

	get_bin_filters() {
		let filters = { disabled: 0 };
		let rack = this.new_rack_control && this.new_rack_control.get_value();
		if (rack) {
			filters.rack = rack;
		}
		return filters;
	}

	make_row_link_control($slot, df) {
		if (!$slot.length) return null;

		let control = frappe.ui.form.make_control({
			parent: $slot,
			df: Object.assign({ fieldtype: "Link" }, df),
			render_input: true,
		});

		this.make_control_compact(control);
		return control;
	}

	make_control_compact(control) {
		let $wrapper = control.$wrapper;
		$wrapper.find(".control-label, .help-box").hide();
		$wrapper.find(".form-group").css({ margin: "0", "min-height": "0" });
		$wrapper.find("input").css({ "min-height": "0" });
		$wrapper.css({ margin: "0", "min-height": "0" });
	}

	on_new_serial_change($tr) {
		if (!this.new_serial_control || !this.new_serial_control.get_value()) return;

		if (this.new_batch_control && !this.new_batch_control.get_value()) {
			this.new_batch_control.$wrapper.find("input").focus();
			return;
		}

		if (this.focus_rack_bin()) return;

		this.commit_new_row($tr);
	}

	on_new_batch_change($tr) {
		if (!this.new_batch_control || !this.new_batch_control.get_value()) return;

		if (this.new_serial_control) {
			if (!this.new_serial_control.get_value()) return;
			if (this.focus_rack_bin()) return;
			this.commit_new_row($tr);
			return;
		}

		if (this.focus_rack_bin()) return;

		let committed = this.commit_new_row($tr);
		committed &&
			committed.then(() => {
				this.wrapper.find(".sbie-qty-input[data-pending-index]").last().focus();
			});
	}

	focus_rack_bin() {
		if (this.new_rack_control && !this.new_rack_control.get_value()) {
			this.new_rack_control.$wrapper.find("input").focus();
			return true;
		}

		if (this.new_bin_control && !this.new_bin_control.get_value()) {
			this.new_bin_control.$wrapper.find("input").focus();
			return true;
		}

		return false;
	}

	on_new_rack_change($tr) {
		if (!this.new_rack_control || !this.new_rack_control.get_value()) return;

		if (this.new_bin_control && !this.new_bin_control.get_value()) {
			this.new_bin_control.$wrapper.find("input").focus();
			return;
		}

		this.commit_from_rack_bin($tr);
	}

	on_new_bin_change($tr) {
		if (!this.new_bin_control || !this.new_bin_control.get_value()) return;
		this.commit_from_rack_bin($tr);
	}

	commit_from_rack_bin($tr) {
		if (this.new_serial_control && !this.new_serial_control.get_value()) return;
		if (this.new_batch_control && !this.new_batch_control.get_value()) return;

		let committed = this.commit_new_row($tr);
		if (committed && !cint(this.item.has_serial_no)) {
			committed.then(() => {
				this.wrapper.find(".sbie-qty-input[data-pending-index]").last().focus();
			});
		}
	}

	edit_batch_cell($td) {
		this.edit_link_cell($td, {
			options: "Batch",
			field: "batch_no",
			placeholder: __("Select Batch No"),
			get_query: () => ({ filters: { item: this.row.item_code, disabled: 0 } }),
		});
	}

	edit_serial_cell($td) {
		this.edit_link_cell($td, {
			options: "Serial No",
			field: "serial_no",
			placeholder: __("Select Serial No"),
			get_query: () => ({ filters: { item_code: this.row.item_code } }),
		});
	}

	edit_rack_cell($td) {
		this.edit_link_cell($td, {
			options: "Rack",
			field: "rack",
			placeholder: __("Select Rack"),
			get_query: () => ({ filters: { disabled: 0 } }),
		});
	}

	edit_bin_cell($td) {
		this.edit_link_cell($td, {
			options: "Bin",
			field: "bin",
			placeholder: __("Select Bin"),
			get_query: () => ({ filters: { disabled: 0 } }),
		});
	}

	edit_link_cell($td, opts) {
		if ($td.data("editing")) return;
		$td.data("editing", 1);

		let name = $td.data("name");
		let current = $td.text().trim();
		$td.empty().addClass("sbie-input-cell").css("cursor", "default");
		this.wrapper.find(".sbie-table").css("overflow", "visible");

		let control = this.make_row_link_control($td, {
			options: opts.options,
			fieldname: "sbie_edit_link",
			placeholder: opts.placeholder,
			get_query: opts.get_query,
			onchange: () => {
				let value = control.get_value();
				if (value && value !== current) {
					this.update_entry(name, { [opts.field]: value });
					this.refresh_view();
				}
			},
		});

		control.set_input(current);
		control.$wrapper.find("input").focus();
	}

	commit_new_row($tr) {
		if ($tr.data("committing") || $tr.data("cancelled")) return;

		let serial_no = this.new_serial_control ? this.new_serial_control.get_value() : "";
		let batch_no = this.new_batch_control ? this.new_batch_control.get_value() : "";
		let rack = this.new_rack_control ? this.new_rack_control.get_value() : "";
		let bin = this.new_bin_control ? this.new_bin_control.get_value() : "";
		if (!serial_no && !batch_no && !rack && !bin) return;

		let qty = serial_no ? 1 : flt($tr.find(".sbie-new-qty").val()) || 1;

		$tr.data("committing", 1);
		this.pending.new_entries.push({ serial_no, batch_no, rack, bin, qty });
		this.frm.dirty();
		return this.go_to_last_page();
	}

	update_entry(name, changes) {
		let updates = this.pending.updates;
		if (!updates[name]) {
			let entry = this.last_entries.find((d) => d.name === name) || {};
			updates[name] = { orig_qty: Math.abs(flt(entry.qty)) };
		}

		Object.assign(updates[name], changes);
		this.frm.dirty();
	}

	bind_events() {
		this.wrapper.find(".sbie-add-row").on("click", () => this.add_new_row());
		this.wrapper.find(".sbie-upload-csv").on("click", () => this.upload_csv());
		this.wrapper.find(".sbie-download-csv").on("click", () => this.download_csv());
		this.wrapper.find(".sbie-prev").on("click", () => this.change_page(-1));
		this.wrapper.find(".sbie-next").on("click", () => this.change_page(1));
		this.wrapper.find(".sbie-first-page").on("click", () => this.go_to_page(1));
		this.wrapper.find(".sbie-last-page").on("click", () => this.go_to_page(this.total_pages));
		this.wrapper
			.find(".sbie-page-number")
			.on("input", (e) => {
				e.target.value = e.target.value.replace(/[^0-9]/g, "");
				e.target.style.width = (e.target.value.length + 1) * 8 + "px";
			})
			.on("keydown", (e) => {
				if (e.which === 13) e.target.blur();
			})
			.on("blur", (e) => this.go_to_page(e.target.value))
			.on("focus", (e) => e.target.select());
		this.wrapper.find(".sbie-delete").on("click", () => this.delete_selected());
		this.wrapper.find(".sbie-scan-action").on("click", () => this.open_scan_dialog());
		this.wrapper.find(".sbie-range-action").on("click", () => this.open_range_dialog());
		this.wrapper.find(".sbie-auto-fetch-action").on("click", () => this.open_auto_fetch_dialog());
	}

	get_type_of_transaction() {
		let doc = this.frm.doc;
		if (doc.doctype === "Stock Entry") {
			return this.row.s_warehouse ? "Outward" : "Inward";
		}

		let inward =
			["Purchase Receipt", "Purchase Invoice", "Stock Reconciliation"].includes(doc.doctype) ||
			this.cdt === "Subcontracting Receipt Item";

		if (doc.is_return) {
			inward = !inward;
		}

		return inward ? "Inward" : "Outward";
	}

	async open_auto_fetch_dialog() {
		let warehouse = this.row.warehouse || this.row.s_warehouse;
		if (!warehouse) {
			frappe.msgprint(__("Please set Warehouse first"));
			return;
		}

		let is_serial = cint(this.item.has_serial_no);
		let based_on = await erpnext.stock.get_pick_serial_batch_based_on();

		let dialog = new frappe.ui.Dialog({
			title: is_serial ? __("Auto Fetch Serial Nos") : __("Auto Fetch Batch Nos"),
			fields: [
				{
					fieldtype: "Float",
					fieldname: "qty",
					label: __("Qty to Fetch"),
					reqd: 1,
					default: Math.abs(flt(this.row[this.qty_field])) || null,
					description: __("Existing entries will be replaced with the fetched entries"),
				},
				{
					fieldtype: "Select",
					fieldname: "based_on",
					label: __("Fetch Based On"),
					options: ["FIFO", "LIFO", "Expiry"],
					default: based_on,
				},
			],
			primary_action_label: __("Fetch"),
			primary_action: (values) => {
				dialog.hide();
				this.auto_fetch_entries(values.qty, values.based_on, warehouse);
			},
		});

		dialog.show();
	}

	async auto_fetch_entries(qty, based_on, warehouse) {
		let data = await this.call("erpnext.stock.serial_batch_bundle.get_auto_data", {
			item_code: this.row.item_code,
			warehouse: warehouse,
			has_serial_no: this.item.has_serial_no,
			has_batch_no: this.item.has_batch_no,
			qty: qty,
			based_on: based_on,
			posting_date: this.frm.doc.posting_date,
			posting_time: this.frm.doc.posting_time,
		});

		if (!data || !data.length) {
			frappe.msgprint(
				__("No stock available for Item {0} in Warehouse {1}", [
					this.esc(this.row.item_code),
					this.esc(warehouse),
				])
			);
			return;
		}

		this.add_auto_fetched_entries(data);
	}

	add_auto_fetched_entries(rows) {
		let p = this.pending;
		p.delete_all = 1;
		p.new_entries = [];
		p.updates = {};
		p.deleted = [];

		for (const row of rows) {
			p.new_entries.push({
				serial_no: row.serial_no || "",
				batch_no: row.batch_no || "",
				qty: Math.abs(flt(row.qty)) || 1,
			});
		}

		this.start = 0;
		this.frm.dirty();
		this.go_to_last_page();
		frappe.show_alert({
			message: __("{0} entries fetched", [p.new_entries.length]),
			indicator: "green",
		});
		this.frm.save();
	}

	open_scan_dialog() {
		if (this.is_rejected && !this.row.rejected_warehouse) {
			frappe.msgprint(__("Please set Rejected Warehouse first"));
			return;
		}

		let is_serial = cint(this.item.has_serial_no);
		let scanned_count = 0;

		let dialog = new frappe.ui.Dialog({
			title: is_serial ? __("Scan Serial Nos") : __("Scan Batch Nos"),
			fields: [
				{
					fieldtype: "Data",
					fieldname: "scan_value",
					options: "Barcode",
					label: is_serial ? __("Scan Serial No") : __("Scan Batch No"),
					description: __("Missing Serial / Batch Nos will be created on Save"),
					onchange: () => {
						let value = (dialog.get_value("scan_value") || "").trim();
						if (!value) return;

						if (this.add_scanned_value(value)) {
							scanned_count++;
						}
						dialog.fields_dict.scanned_info.$wrapper.html(
							`<div class="text-muted small">${__("Scanned: {0}", [
								scanned_count,
							])} &middot; ${frappe.utils.escape_html(value)}</div>`
						);
						dialog.set_value("scan_value", "");
					},
				},
				{ fieldtype: "HTML", fieldname: "scanned_info" },
			],
			on_hide: () => this.refresh_view(),
		});

		dialog.show();
	}

	get_active_server_row(field, value) {
		let p = this.pending;
		if (p.delete_all) return null;

		return this.last_entries.find((d) => d[field] === value && !p.deleted.some((x) => x.name === d.name));
	}

	get_known_identifiers() {
		let p = this.pending;
		let known = new Set(p.new_entries.map((d) => d.serial_no || d.batch_no));

		if (!p.delete_all) {
			let deleted = new Set(p.deleted.map((d) => d.name));
			for (const d of this.last_entries) {
				if (!deleted.has(d.name)) {
					known.add(d.serial_no || d.batch_no);
				}
			}
		}

		return known;
	}

	add_scanned_value(value) {
		let p = this.pending;

		if (cint(this.item.has_serial_no)) {
			if (this.get_known_identifiers().has(value)) {
				frappe.show_alert({
					message: __("Serial No {0} already added", [this.esc(value)]),
					indicator: "orange",
				});
				return false;
			}

			p.new_entries.push({ serial_no: value, batch_no: "", qty: 1 });
		} else {
			let existing = p.new_entries.find((d) => d.batch_no === value);
			let server_row = this.get_active_server_row("batch_no", value);
			if (existing) {
				existing.qty = flt(existing.qty) + 1;
			} else if (server_row) {
				let update = p.updates[server_row.name];
				let current = update && update.qty != null ? flt(update.qty) : Math.abs(flt(server_row.qty));
				this.update_entry(server_row.name, { qty: current + 1 });
			} else {
				p.new_entries.push({ serial_no: "", batch_no: value, qty: 1 });
			}
		}

		this.frm.dirty();
		this.go_to_last_page();
		return true;
	}

	open_range_dialog() {
		if (this.is_rejected && !this.row.rejected_warehouse) {
			frappe.msgprint(__("Please set Rejected Warehouse first"));
			return;
		}

		let dialog = new frappe.ui.Dialog({
			title: __("Create Serial Nos from Range"),
			fields: [
				{
					fieldtype: "Data",
					fieldname: "serial_no_range",
					label: __("Serial No Range"),
					reqd: 1,
					description: __(
						'"SN-01::10" for "SN-01" to "SN-10". Missing Serial Nos will be created on Save'
					),
				},
			],
			primary_action_label: __("Add"),
			primary_action: ({ serial_no_range }) => {
				let serial_nos = erpnext.stock.utils.get_serial_range(serial_no_range, "::");
				if (!serial_nos || !serial_nos.length) {
					frappe.throw(__("Invalid range. Use the format {0}", ["SN-01::10"]));
				}

				dialog.hide();
				this.add_serial_range(serial_nos);
			},
		});

		dialog.show();
	}

	add_serial_range(serial_nos) {
		let p = this.pending;
		let known = this.get_known_identifiers();

		let added = 0;
		for (const serial_no of serial_nos) {
			if (known.has(serial_no)) continue;
			p.new_entries.push({ serial_no: serial_no, batch_no: "", qty: 1 });
			added++;
		}

		this.frm.dirty();
		this.go_to_last_page();
		frappe.show_alert({
			message: __("{0} Serial Nos added. They will be saved with the document.", [added]),
			indicator: "green",
		});
	}

	get total_pages() {
		return Math.ceil(this.get_effective_count() / this.page_length) || 1;
	}

	go_to_last_page() {
		this.start = (this.total_pages - 1) * this.page_length;
		return this.load_page();
	}

	change_page(direction) {
		let current_page = Math.floor(this.start / this.page_length) + 1;
		this.go_to_page(current_page + direction);
	}

	go_to_page(index) {
		index = Math.min(Math.max(cint(index) || 1, 1), this.total_pages);
		let new_start = (index - 1) * this.page_length;

		if (new_start === this.start) {
			this.wrapper.find(".sbie-page-number").val(index);
			return;
		}

		this.start = new_start;
		this.load_page();
	}

	async load_page() {
		if (this.frm.doc.__islocal || !this.row.name || this.row.name.startsWith("new-") || !this.warehouse) {
			// Unsaved parent/row - there is no real voucher_detail_no to key ledger rows by yet.
			this.server_total_count = 0;
			this.server_total_qty = 0;
			this.last_entries = [];
			this._totals_loaded = true;
			await this.seed_from_amended_document();
		} else if (!this._totals_loaded || this.start < this.server_total_count) {
			let data = await this.call("erpnext.stock.serial_batch_inline_editor.get_ledger_entries", {
				voucher_type: this.frm.doc.doctype,
				voucher_no: this.frm.doc.name,
				voucher_detail_no: this.row.name,
				warehouse: this.warehouse,
				start: this.start,
				page_length: this.page_length,
			});
			this.server_total_count = data.total_count;
			this.server_total_qty = flt(data.total_qty);
			this.last_entries = data.entries;
			this._totals_loaded = true;
		} else {
			this.last_entries = [];
		}

		this.refresh_view();
		this.reconcile_row_qty();
	}

	async seed_from_amended_document() {
		let p = this.pending;
		if (!this.frm.doc.amended_from || p.seeded_amend || this.has_pending() || !this.warehouse) return;

		p.seeded_amend = 1;
		let entries = await this.call("erpnext.stock.serial_batch_inline_editor.get_amended_ledger_entries", {
			voucher_type: this.frm.doc.doctype,
			amended_from: this.frm.doc.amended_from,
			child_doctype: this.cdt,
			idx: this.row.idx,
			warehouse: this.warehouse,
		});

		if (entries && entries.length) {
			p.new_entries = entries.map((d) => ({
				serial_no: d.serial_no || "",
				batch_no: d.batch_no || "",
				rack: d.rack || "",
				bin: d.bin || "",
				qty: Math.abs(flt(d.qty)) || 1,
			}));
		}
	}

	refresh_view() {
		this.render_rows(this.last_entries);
		this.update_summary();
		this.sync_row_qty();
	}

	get_effective_count() {
		let p = this.pending;
		if (p.delete_all) {
			return p.new_entries.length;
		}

		return this.server_total_count + p.new_entries.length - p.deleted.length;
	}

	get_effective_qty() {
		let p = this.pending;
		let qty = p.delete_all ? 0 : this.server_total_qty;

		for (const row of p.new_entries) {
			qty += flt(row.qty);
		}

		if (!p.delete_all) {
			for (const name in p.updates) {
				const u = p.updates[name];
				if (u.qty != null) {
					qty += flt(u.qty) - flt(u.orig_qty);
				}
			}
			for (const d of p.deleted) {
				qty -= flt(d.qty);
			}
		}

		return flt(qty, cint(frappe.boot.sysdefaults && frappe.boot.sysdefaults.float_precision) || 3);
	}

	sync_row_qty() {
		if (!this.has_serial_batch) return;
		if (this.frm.doc.docstatus !== 0 || !this.has_pending()) return;

		let expected = this.get_effective_qty();
		if (flt(this.row[this.qty_field]) !== expected) {
			frappe.model.set_value(this.cdt, this.cdn, this.qty_field, expected);
		}
	}

	reconcile_row_qty() {
		if (!this.has_serial_batch) return;
		if (this.frm.doc.docstatus !== 0 || this.has_pending() || !this.server_total_count) return;

		if (flt(this.row[this.qty_field]) !== this.server_total_qty) {
			frappe.model.set_value(this.cdt, this.cdn, this.qty_field, this.server_total_qty);
			frappe.show_alert({
				message: __(
					"Qty updated to {0} to match the serial / batch entries. Please save the document.",
					[this.server_total_qty]
				),
				indicator: "orange",
			});
		}
	}

	render_rows(entries) {
		let p = this.pending;
		let show_batch = cint(this.item.has_batch_no);
		let show_serial = cint(this.item.has_serial_no);
		let show_rack = this.show_rack_bin ? 1 : 0;
		let column_count = 3 + show_serial + show_batch + 2 * show_rack;
		let qty_editable = (d) => !d.serial_no && (show_batch || show_rack);

		let header = `<thead><tr>
			<th style="width: 36px; text-align: center;"><input type="checkbox" class="sbie-check-all"></th>
			<th style="width: 48px; text-align: center;">${__("No")}</th>
			${show_serial ? `<th>${__("Serial No")}</th>` : ""}
			${show_batch ? `<th>${__("Batch No")}</th>` : ""}
			${show_rack ? `<th>${__("Rack")}</th><th>${__("Bin")}</th>` : ""}
			<th style="width: 110px; text-align: right;">${__("Qty")}</th>
		</tr></thead>`;

		let visible = p.delete_all ? [] : entries.filter((d) => !p.deleted.some((x) => x.name === d.name));
		let body = visible
			.map((d, i) => {
				let update = p.updates[d.name] || {};
				let qty = update.qty != null ? flt(update.qty) : Math.abs(flt(d.qty));
				let batch_no = this.esc(update.batch_no || d.batch_no || "");
				let serial_no = this.esc(update.serial_no || d.serial_no || "");
				let rack = this.esc(update.rack || d.rack || "");
				let bin = this.esc(update.bin || d.bin || "");
				let name = this.esc(d.name);

				return `<tr data-name="${name}">
				<td style="text-align: center;">
					<input type="checkbox" class="sbie-check" data-name="${name}" data-qty="${qty}"></td>
				<td style="text-align: center;">${this.start + i + 1}</td>
				${
					show_serial
						? `<td class="sbie-serial-cell" data-name="${name}" title="${__(
								"Click to change Serial No"
						  )}" style="cursor: pointer;">${serial_no}</td>`
						: ""
				}
				${
					show_batch
						? `<td class="sbie-batch-cell" data-name="${name}" title="${__(
								"Click to change Batch No"
						  )}" style="cursor: pointer;">${batch_no}</td>`
						: ""
				}
				${
					show_rack
						? `<td class="sbie-rack-cell" data-name="${name}" title="${__(
								"Click to change Rack"
						  )}" style="cursor: pointer;">${rack}</td>
						<td class="sbie-bin-cell" data-name="${name}" title="${__(
								"Click to change Bin"
						  )}" style="cursor: pointer;">${bin}</td>`
						: ""
				}
				<td class="${qty_editable(d) ? "sbie-input-cell" : ""}" style="text-align: right;">${
					qty_editable(d) ? this.get_qty_input(d, qty) : this.format_float(qty)
				}</td>
			</tr>`;
			})
			.join("");

		let base_count = p.delete_all ? 0 : this.server_total_count - p.deleted.length;
		let pending_offset = Math.max(0, this.start - (p.delete_all ? 0 : this.server_total_count));
		let capacity = Math.max(this.page_length - visible.length, 0);
		body += p.new_entries
			.slice(pending_offset, pending_offset + capacity)
			.map((d, i) => {
				let index = pending_offset + i;
				return `<tr data-pending-index="${index}">
				<td style="text-align: center;">
					<input type="checkbox" class="sbie-check" data-pending-index="${index}"></td>
				<td style="text-align: center;">${base_count + index + 1}</td>
				${show_serial ? `<td>${this.esc(d.serial_no || "")}</td>` : ""}
				${show_batch ? `<td>${this.esc(d.batch_no || "")}</td>` : ""}
				${show_rack ? `<td>${this.esc(d.rack || "")}</td><td>${this.esc(d.bin || "")}</td>` : ""}
				<td class="${qty_editable(d) ? "sbie-input-cell" : ""}" style="text-align: right;">${
					qty_editable(d) ? this.get_pending_qty_input(d, index) : this.format_float(d.qty)
				}</td>
			</tr>`;
			})
			.join("");

		if (!visible.length && !p.new_entries.length) {
			body = `<tr class="sbie-empty"><td colspan="${column_count}" style="text-align: center;">
				${
					this.has_serial_batch
						? __("Click on 'Add row' to add Serial / Batch entries")
						: __("Click on 'Add row' to add Rack / Bin entries")
				}</td></tr>`;
		}

		this.wrapper
			.find(".sbie-table")
			.css("overflow", "")
			.html(`<table>${header}<tbody>${body}</tbody></table>`);

		this.wrapper.find(".sbie-check-all").on("change", (e) => {
			this.wrapper.find(".sbie-check").prop("checked", e.target.checked);
			this.toggle_delete_button();
		});
		this.wrapper.find(".sbie-check").on("change", (e) => {
			if (!e.target.checked) {
				this.wrapper.find(".sbie-check-all").prop("checked", false);
			}
			this.toggle_delete_button();
		});
		this.wrapper.find(".sbie-batch-cell").on("click", (e) => this.edit_batch_cell($(e.currentTarget)));
		this.wrapper.find(".sbie-serial-cell").on("click", (e) => this.edit_serial_cell($(e.currentTarget)));
		this.wrapper.find(".sbie-rack-cell").on("click", (e) => this.edit_rack_cell($(e.currentTarget)));
		this.wrapper.find(".sbie-bin-cell").on("click", (e) => this.edit_bin_cell($(e.currentTarget)));
		this.wrapper.find(".sbie-qty-input").on("input", (e) => this.restrict_to_numeric(e));
		this.wrapper.find(".sbie-qty-input").on("blur", (e) => this.apply_float_format(e));
		this.wrapper.find(".sbie-qty-input").on("change", (e) => this.update_qty(e));
		this.wrapper.find(".sbie-qty-input").on("focus", (e) => e.target.select());
		this.toggle_delete_button();
	}

	get_qty_input(d, qty) {
		return `<input type="text" class="sbie-qty-input" data-fieldtype="Float"
			data-name="${this.esc(d.name)}" value="${this.format_float(qty)}" style="text-align: right;">`;
	}

	get_pending_qty_input(d, index) {
		return `<input type="text" class="sbie-qty-input" data-fieldtype="Float"
			data-pending-index="${index}" value="${this.format_float(d.qty)}" style="text-align: right;">`;
	}

	format_float(value) {
		let precision = cint(frappe.boot.sysdefaults && frappe.boot.sysdefaults.float_precision) || 3;
		let formatted = flt(value, precision).toFixed(precision).replace(/0+$/, "");
		if (formatted.endsWith(".")) {
			formatted += "0";
		}
		return formatted;
	}

	restrict_to_numeric(e) {
		let $input = $(e.target);
		let value = $input
			.val()
			.replace(/[^0-9.]/g, "")
			.replace(/(\..*)\./g, "$1");
		if (value !== $input.val()) {
			$input.val(value);
		}
	}

	apply_float_format(e) {
		let $input = $(e.target);
		if ($input.val() !== "") {
			$input.val(this.format_float($input.val()));
		}
	}

	toggle_delete_button() {
		let checked = this.wrapper.find(".sbie-check:checked").length;
		let select_all = this.wrapper.find(".sbie-check-all").prop("checked");
		this.wrapper
			.find(".sbie-delete")
			.toggleClass("hidden", !checked)
			.text(select_all ? __("Delete All") : __("Delete row"));
	}

	update_summary() {
		this.total_count = this.server_total_count;
		this.wrapper.find(".sbie-summary").text(__("Total Qty: {0}", [this.get_effective_qty()]));

		let current_page = Math.floor(this.start / this.page_length) + 1;
		this.wrapper
			.find(".sbie-pagination")
			.toggleClass("hidden", this.get_effective_count() <= this.page_length);
		this.wrapper
			.find(".sbie-page-number")
			.val(current_page)
			.css("width", (String(current_page).length + 1) * 8 + "px");
		this.wrapper.find(".sbie-total-pages").text(this.total_pages);
	}

	update_qty(e) {
		let $input = $(e.target);
		let qty = flt($input.val()) || 1;

		if ($input.data("pending-index") != null) {
			this.pending.new_entries[$input.data("pending-index")].qty = qty;
		} else {
			this.update_entry($input.data("name"), { qty: qty });
		}

		this.update_summary();
		this.sync_row_qty();
	}

	delete_selected() {
		if (this.wrapper.find(".sbie-check-all").prop("checked")) {
			this.delete_all_entries();
			return;
		}

		let p = this.pending;
		let pending_indexes = [];

		this.wrapper.find(".sbie-check:checked").each((_, el) => {
			let $el = $(el);
			if ($el.data("pending-index") != null) {
				pending_indexes.push($el.data("pending-index"));
			} else if ($el.data("name")) {
				let name = $el.data("name");
				delete p.updates[name];
				p.deleted.push({ name: name, qty: flt($el.data("qty")) });
			}
		});

		p.new_entries = p.new_entries.filter((_, i) => !pending_indexes.includes(i));
		this.frm.dirty();
		this.refresh_view();
	}

	delete_all_entries() {
		frappe.confirm(
			__("This will delete all {0} entries. Continue?", [this.get_effective_count()]),
			() => {
				let p = this.pending;
				p.delete_all = 1;
				p.new_entries = [];
				p.updates = {};
				p.deleted = [];
				this.frm.dirty();
				this.start = 0;
				this.refresh_view();
			}
		);
	}

	async upsert({ entries = [], deleted = [], replace = 0 }) {
		if (this.frm.doc.__islocal || !this.row.name || this.row.name.startsWith("new-")) {
			frappe.msgprint(
				__("Please save the document first, then select Serial / Batch entries for this row.")
			);
			return;
		}

		let summary = await this.call("erpnext.stock.serial_batch_inline_editor.upsert_bundle_entries", {
			child_row: Object.assign({}, this.row, { is_rejected: this.is_rejected }),
			doc: this.frm.doc,
			entries: entries,
			deleted: deleted,
			replace: replace,
		});

		await frappe.model.set_value(this.cdt, this.cdn, this.qty_field, summary.total_qty);

		this._totals_loaded = false;
		await this.load_page();
	}

	call(method, args) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: method,
				args: args,
				callback: (r) => resolve(r.message),
				error: reject,
			});
		});
	}
};

erpnext.stock.SBIE_DOCTYPES = [
	{ parent: "Purchase Receipt", child: "Purchase Receipt Item", table: "items" },
	{ parent: "Purchase Invoice", child: "Purchase Invoice Item", table: "items" },
	{ parent: "Sales Invoice", child: "Sales Invoice Item", table: "items" },
	{ parent: "Sales Invoice", child: "Packed Item", table: "packed_items" },
	{ parent: "POS Invoice", child: "POS Invoice Item", table: "items" },
	{ parent: "POS Invoice", child: "Packed Item", table: "packed_items" },
	{ parent: "Delivery Note", child: "Delivery Note Item", table: "items" },
	{ parent: "Delivery Note", child: "Packed Item", table: "packed_items" },
	{ parent: "Stock Entry", child: "Stock Entry Detail", table: "items" },
	{ parent: "Stock Reconciliation", child: "Stock Reconciliation Item", table: "items" },
	{ parent: "Subcontracting Receipt", child: "Subcontracting Receipt Item", table: "items" },
	{
		parent: "Subcontracting Receipt",
		child: "Subcontracting Receipt Supplied Item",
		table: "supplied_items",
		qty_field: "consumed_qty",
	},
	{ parent: "Pick List", child: "Pick List Item", table: "locations" },
	{
		parent: "Asset Capitalization",
		child: "Asset Capitalization Stock Item",
		table: "stock_items",
		qty_field: "stock_qty",
	},
	{
		parent: "Asset Repair",
		child: "Asset Repair Consumed Item",
		table: "stock_items",
		qty_field: "consumed_quantity",
	},
];

erpnext.stock.get_sbie_config = function (doctype, child_doctype) {
	return erpnext.stock.SBIE_DOCTYPES.find((d) => d.parent === doctype && d.child === child_doctype);
};

erpnext.stock.get_sbie_row = function (frm, cdn) {
	for (let config of erpnext.stock.SBIE_DOCTYPES) {
		if (config.parent !== frm.doc.doctype) continue;

		let row = (frm.doc[config.table] || []).find((d) => d.name === cdn);
		if (row) return { row, config };
	}

	return {};
};

erpnext.stock.get_sbie_warehouse = function (row, is_rejected) {
	if (is_rejected) {
		return row.rejected_warehouse;
	}

	return row.warehouse || row.s_warehouse || row.t_warehouse;
};

erpnext.stock.get_sbie_pending_map = function (frm) {
	let store = (frm._sbie_pending = frm._sbie_pending || {});
	return (store[frm.doc.name] = store[frm.doc.name] || {});
};

erpnext.stock.flush_serial_batch_pending = async function (frm) {
	let pending_map = erpnext.stock.get_sbie_pending_map(frm);

	for (let key of Object.keys(pending_map)) {
		let p = pending_map[key];
		let has_changes =
			p.delete_all || p.new_entries.length || p.deleted.length || Object.keys(p.updates).length;
		if (!has_changes) {
			delete pending_map[key];
			continue;
		}

		let [cdn, is_rejected] = key.split("::");
		is_rejected = cint(is_rejected);
		let { row, config } = erpnext.stock.get_sbie_row(frm, cdn);
		if (!row) {
			delete pending_map[key];
			continue;
		}

		let qty_field = is_rejected ? "rejected_qty" : config.qty_field || "qty";

		if (frm.doc.__islocal || !row.name || row.name.startsWith("new-")) {
			if (erpnext.stock.stash_pending_for_after_save(frm, row, config, p, is_rejected)) {
				continue;
			}

			// No real voucher_no/voucher_detail_no exists yet to key Stock Location Ledger rows
			// by - carry the selection on the row's own plain fields instead, same fallback the
			// server side uses for pre-insert composition (e.g. Work Order mapping).
			erpnext.stock.apply_sbie_pending_as_plain_fields(row, p, qty_field);
			delete pending_map[key];
			continue;
		}

		let entries = p.new_entries.concat(
			Object.keys(p.updates).map((name) => {
				let update = { name: name };
				if (p.updates[name].qty != null) update.qty = p.updates[name].qty;
				for (let field of ["serial_no", "batch_no", "rack", "bin"]) {
					if (p.updates[name][field]) update[field] = p.updates[name][field];
				}
				return update;
			})
		);

		let summary = await frappe.xcall("erpnext.stock.serial_batch_inline_editor.upsert_bundle_entries", {
			child_row: Object.assign({}, row, { is_rejected: is_rejected }),
			doc: frm.doc,
			entries: entries,
			deleted: p.deleted.map((d) => d.name),
			replace: cint(p.delete_all),
		});

		row[qty_field] = summary.total_qty;
		if (row.received_qty != null) {
			row.received_qty = flt(row.qty) + flt(row.rejected_qty);
		}
		delete pending_map[key];
	}
};

erpnext.stock.stash_pending_for_after_save = function (frm, row, config, pending, is_rejected) {
	// Rack/bin (and amended-document prefills) can't ride on the row's plain serial/batch text
	// fields - hold them until the save assigns real row names, then write the ledger drafts.
	let needs_ledger = pending.seeded_amend || pending.new_entries.some((e) => e.rack || e.bin);
	if (!needs_ledger) return false;

	let stash = (frm._sbie_after_save = frm._sbie_after_save || []);
	let existing = stash.find(
		(d) => d.table === config.table && d.idx === row.idx && d.is_rejected === is_rejected
	);
	if (existing) {
		existing.entries = pending.new_entries;
	} else {
		stash.push({
			table: config.table,
			idx: row.idx,
			is_rejected: is_rejected,
			entries: pending.new_entries,
		});
	}

	return true;
};

erpnext.stock.flush_after_save_entries = async function (frm) {
	let stash = frm._sbie_after_save;
	if (!stash || !stash.length) return;

	frm._sbie_after_save = [];
	for (let d of stash) {
		let row = (frm.doc[d.table] || []).find((r) => r.idx === d.idx);
		if (!row || !d.entries.length) continue;

		await frappe.xcall("erpnext.stock.serial_batch_inline_editor.upsert_bundle_entries", {
			child_row: Object.assign({}, row, { is_rejected: d.is_rejected }),
			doc: frm.doc,
			entries: d.entries,
			replace: 1,
		});
	}
};

erpnext.stock.apply_sbie_pending_as_plain_fields = function (row, pending, qty_field) {
	row.use_serial_batch_fields = 1;

	if (pending.delete_all) {
		row.serial_no = null;
		row.batch_no = null;
		row[qty_field] = 0;
		return;
	}

	let serial_nos = pending.new_entries.filter((e) => e.serial_no).map((e) => e.serial_no);
	if (serial_nos.length) {
		row.serial_no = serial_nos.join("\n");
		row[qty_field] = serial_nos.length;
	}

	let batch_entry = pending.new_entries.find((e) => e.batch_no);
	if (batch_entry) {
		row.batch_no = batch_entry.batch_no;
		if (!serial_nos.length) {
			row[qty_field] = flt(batch_entry.qty) || 1;
		}
	}
};

erpnext.stock.mount_stock_location_editor = async function (frm, cdt, cdn) {
	let config = erpnext.stock.get_sbie_config(frm.doc.doctype, cdt);
	if (!config || !frm.fields_dict[config.table]) return;

	let grid_row = frm.fields_dict[config.table].grid.grid_rows_by_docname[cdn];
	let grid_form = grid_row && grid_row.grid_form;
	if (!grid_form) return;

	let editors = [
		{ fieldname: "serial_batch_entries_html", is_rejected: 0 },
		{ fieldname: "rejected_serial_batch_entries_html", is_rejected: 1 },
	];

	let row = locals[cdt][cdn];
	let show = Boolean(row) && frm.doc.docstatus === 0;
	if (show && row.use_serial_batch_fields && row.item_code) {
		let item = await erpnext.stock.get_sbie_item_flags(row.item_code);
		show = !cint(item.has_serial_no) && !cint(item.has_batch_no);
	}

	erpnext.stock.toggle_legacy_bundle_fields(grid_form, show);

	let editors_store = (frm._sbie_editors = frm._sbie_editors || {});

	for (let editor of editors) {
		let field = grid_form.fields_dict[editor.fieldname];
		if (!field) continue;

		if (!show) {
			field.$wrapper.closest(".form-section").hide();
			continue;
		}

		let key = `${cdn}::${editor.is_rejected}`;
		let existing = editors_store[key];
		if (
			existing &&
			existing.wrapper[0] === field.$wrapper[0] &&
			document.body.contains(field.$wrapper[0]) &&
			existing.wrapper.find(".serial-batch-inline-editor").length
		) {
			continue;
		}

		editors_store[key] = new erpnext.stock.StockLocationEditor({
			frm,
			cdt,
			cdn,
			wrapper: field.$wrapper,
			is_rejected: editor.is_rejected,
		});
	}
};

erpnext.stock.toggle_legacy_bundle_fields = function (grid_form, editor_active) {
	let legacy_fields = [
		"add_serial_batch_bundle",
		"pick_serial_and_batch",
		"add_serial_batch_for_rejected_qty",
	];

	for (let fieldname of legacy_fields) {
		let field = grid_form.fields_dict[fieldname];
		if (!field) continue;

		if (editor_active) {
			field.$wrapper.hide();
		} else {
			field.refresh();
		}
	}
};

erpnext.stock.setup_serial_batch_pending_flush = function (doctype) {
	frappe.ui.form.on(doctype, {
		validate(frm) {
			return erpnext.stock.flush_serial_batch_pending(frm);
		},
		after_save(frm) {
			return erpnext.stock.flush_after_save_entries(frm);
		},
	});
};

erpnext.stock.setup_inline_serial_batch_editor = function () {
	new Set(erpnext.stock.SBIE_DOCTYPES.map((d) => d.parent)).forEach((doctype) =>
		erpnext.stock.setup_serial_batch_pending_flush(doctype)
	);

	new Set(erpnext.stock.SBIE_DOCTYPES.map((d) => d.child)).forEach((child_doctype) => {
		frappe.ui.form.on(child_doctype, {
			form_render(frm, cdt, cdn) {
				erpnext.stock.mount_stock_location_editor(frm, cdt, cdn);
			},
			use_serial_batch_fields(frm, cdt, cdn) {
				erpnext.stock.mount_stock_location_editor(frm, cdt, cdn);
			},
		});
	});
};

erpnext.stock.setup_inline_serial_batch_editor();

erpnext.stock.get_sbie_item_flags = async function (item_code) {
	let cache = (erpnext.stock._sbie_item_flags = erpnext.stock._sbie_item_flags || {});
	if (!cache[item_code]) {
		let { message } = await frappe.db.get_value("Item", item_code, ["has_serial_no", "has_batch_no"]);
		cache[item_code] = message || {};
	}

	return cache[item_code];
};

erpnext.stock.is_rack_and_bin_enabled = async function () {
	if (erpnext.stock._rack_and_bin_enabled === undefined) {
		let { message } = await frappe.db.get_value(
			"Stock Settings",
			"Stock Settings",
			"enable_rack_and_bin"
		);
		erpnext.stock._rack_and_bin_enabled = cint(message && message.enable_rack_and_bin);
	}

	return erpnext.stock._rack_and_bin_enabled;
};

erpnext.stock.get_pick_serial_batch_based_on = async function () {
	if (erpnext.stock._pick_serial_batch_based_on === undefined) {
		let { message } = await frappe.db.get_value(
			"Stock Settings",
			"Stock Settings",
			"pick_serial_and_batch_based_on"
		);
		erpnext.stock._pick_serial_batch_based_on =
			(message && message.pick_serial_and_batch_based_on) || "FIFO";
	}

	return erpnext.stock._pick_serial_batch_based_on;
};
