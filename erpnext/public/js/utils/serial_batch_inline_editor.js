frappe.provide("erpnext.stock");

erpnext.stock.SerialBatchInlineEditor = class SerialBatchInlineEditor {
	constructor({ frm, cdt, cdn, wrapper, is_rejected }) {
		this.frm = frm;
		this.cdt = cdt;
		this.cdn = cdn;
		this.wrapper = $(wrapper);
		this.is_rejected = cint(is_rejected);
		this.bundle_field = this.is_rejected ? "rejected_serial_and_batch_bundle" : "serial_and_batch_bundle";
		this.qty_field = this.is_rejected ? "rejected_qty" : "qty";
		this.start = 0;
		this.page_length = 10;
		this.total_count = 0;
		this.make();
	}

	get row() {
		return locals[this.cdt][this.cdn];
	}

	get bundle() {
		return this.row[this.bundle_field];
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

		this.item = await frappe.db.get_value("Item", this.row.item_code, ["has_serial_no", "has_batch_no"]);
		this.item = this.item.message || {};

		if (!cint(this.item.has_serial_no) && !cint(this.item.has_batch_no)) {
			this.wrapper.empty();
			this.toggle_section(false);
			return;
		}

		this.toggle_section(true);
		this.render_skeleton();
		this.make_serial_control();
		this.make_batch_control();
		this.load_page();
	}

	render_skeleton() {
		this.wrapper.html(`
			<style>
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
					height: 28px;
					border: none;
					box-shadow: none;
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
			</style>
			<div class="serial-batch-inline-editor">
				<div class="sbie-toolbar" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 10px;">
					${this.get_toolbar_html()}
				</div>
				<div class="sbie-table"></div>
				<div class="sbie-footer" style="display: flex; gap: 8px; align-items: center; margin-top: 10px;">
					<button class="btn btn-sm btn-default sbie-prev" style="height: 28px; padding: 2px 10px;">
						${__("Prev")}</button>
					<span class="sbie-page-info text-muted small"></span>
					<button class="btn btn-sm btn-default sbie-next" style="height: 28px; padding: 2px 10px;">
						${__("Next")}</button>
					<button class="btn btn-sm btn-danger sbie-delete hidden"
						style="height: 28px; padding: 2px 10px; white-space: nowrap;">${__("Delete Selected")}</button>
					<div class="sbie-summary text-muted small" style="margin-left: auto;"></div>
				</div>
			</div>
		`);
		this.bind_events();
	}

	get_toolbar_html() {
		let html = "";
		if (cint(this.item.has_serial_no)) {
			html += `<div class="sbie-serial-slot" style="width: 220px;"></div>`;
		}
		if (cint(this.item.has_batch_no)) {
			html += `<div class="sbie-batch-slot" style="width: 180px;"></div>`;
			if (!cint(this.item.has_serial_no)) {
				html += `<input type="text" class="form-control sbie-qty" data-fieldtype="Float"
					style="height: 28px; max-width: 90px; text-align: right;" placeholder="${__("Qty")}">`;
			}
		}
		html += `<button class="btn btn-sm btn-default sbie-add" style="height: 28px; padding: 2px 12px;">
			${__("Add")}</button>`;
		html += `<button class="btn btn-sm btn-default sbie-upload-csv"
			style="height: 28px; padding: 2px 12px; white-space: nowrap;">${__("Upload CSV")}</button>`;
		html += `<button class="btn btn-sm btn-default sbie-download-csv"
			style="height: 28px; padding: 2px 12px; white-space: nowrap;">${__("Download CSV")}</button>`;
		return html;
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
		if (this.bundle) {
			url = `/api/method/erpnext.stock.doctype.serial_and_batch_bundle.inline_editor.download_bundle_entries_csv?bundle=${encodeURIComponent(
				this.bundle
			)}`;
		} else {
			url = `/api/method/erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.download_blank_csv_template?content=${encodeURIComponent(
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
		let data = await this.call(
			"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.upload_csv_file",
			{ item_code: this.row.item_code, file_path: file_url }
		);

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

		if (this.total_count) {
			frappe.confirm(
				__("This will replace the existing {0} entries. Continue?", [this.total_count]),
				() => this.replace_entries(entries)
			);
		} else {
			this.replace_entries(entries);
		}
	}

	async replace_entries(entries) {
		await this.upsert({ entries, replace: 1 });
		if (this.frm.is_dirty()) {
			this.frm.save();
		}
	}

	make_serial_control() {
		if (!cint(this.item.has_serial_no)) return;

		this.serial_control = frappe.ui.form.make_control({
			parent: this.wrapper.find(".sbie-serial-slot"),
			df: {
				fieldtype: "Link",
				options: "Serial No",
				fieldname: "sbie_serial",
				placeholder: __("Scan / select Serial No"),
				get_query: () => {
					return { filters: { item_code: this.row.item_code } };
				},
			},
			render_input: true,
		});

		this.make_control_compact(this.serial_control);
		this.serial_control.$wrapper.find("input").on("keypress", (e) => {
			if (e.which === 13) this.add_entries();
		});
	}

	make_batch_control() {
		if (!cint(this.item.has_batch_no)) return;

		this.batch_control = frappe.ui.form.make_control({
			parent: this.wrapper.find(".sbie-batch-slot"),
			df: {
				fieldtype: "Link",
				options: "Batch",
				fieldname: "sbie_batch",
				placeholder: __("Batch No"),
				get_query: () => {
					return { filters: { item: this.row.item_code, disabled: 0 } };
				},
			},
			render_input: true,
		});

		this.make_control_compact(this.batch_control);
	}

	make_control_compact(control) {
		let $wrapper = control.$wrapper;
		$wrapper.find(".control-label, .help-box").hide();
		$wrapper.find(".form-group").css("margin", "0");
		$wrapper.find("input").css({ height: "28px", "background-color": "var(--control-bg)" });
		$wrapper.css("margin", "0");
	}

	bind_events() {
		this.wrapper.find(".sbie-add").on("click", () => this.add_entries());
		this.wrapper.find(".sbie-upload-csv").on("click", () => this.upload_csv());
		this.wrapper.find(".sbie-download-csv").on("click", () => this.download_csv());
		this.wrapper.find(".sbie-qty").on("input", (e) => this.restrict_to_numeric(e));
		this.wrapper.find(".sbie-qty").on("blur", (e) => this.apply_float_format(e));
		this.wrapper.find(".sbie-qty").on("focus", (e) => e.target.select());
		this.wrapper.find(".sbie-prev").on("click", () => this.change_page(-1));
		this.wrapper.find(".sbie-next").on("click", () => this.change_page(1));
		this.wrapper.find(".sbie-delete").on("click", () => this.delete_selected());
	}

	change_page(direction) {
		let new_start = this.start + direction * this.page_length;
		if (new_start < 0 || new_start >= this.total_count) return;

		this.start = new_start;
		this.load_page();
	}

	async load_page() {
		if (!this.bundle) {
			this.render_rows([]);
			this.update_summary({ total_count: 0, total_qty: 0 });
			return;
		}

		let data = await this.call(
			"erpnext.stock.doctype.serial_and_batch_bundle.inline_editor.get_bundle_entries",
			{
				bundle: this.bundle,
				start: this.start,
				page_length: this.page_length,
			}
		);

		this.render_rows(data.entries);
		this.update_summary(data);
		this.reconcile_row_qty(data);
	}

	reconcile_row_qty(data) {
		if (this.frm.doc.docstatus !== 0 || !data.total_count) return;

		if (flt(this.row[this.qty_field]) !== flt(data.total_qty)) {
			frappe.model.set_value(this.cdt, this.cdn, this.qty_field, data.total_qty);
			frappe.show_alert({
				message: __(
					"Qty updated to {0} to match the Serial and Batch Bundle. Please save the document.",
					[data.total_qty]
				),
				indicator: "orange",
			});
		}
	}

	render_rows(entries) {
		let show_batch = cint(this.item.has_batch_no);
		let show_serial = cint(this.item.has_serial_no);
		let column_count = 3 + show_serial + show_batch;

		let header = `<thead><tr>
			<th style="width: 36px; text-align: center;"><input type="checkbox" class="sbie-check-all"></th>
			<th style="width: 48px; text-align: center;">${__("No")}</th>
			${show_serial ? `<th>${__("Serial No")}</th>` : ""}
			${show_batch ? `<th>${__("Batch No")}</th>` : ""}
			<th style="width: 110px; text-align: right;">${__("Qty")}</th>
		</tr></thead>`;

		let body = entries
			.map(
				(d, i) => `<tr data-name="${d.name}">
				<td style="text-align: center;"><input type="checkbox" class="sbie-check" data-name="${d.name}"></td>
				<td style="text-align: center;">${this.start + i + 1}</td>
				${show_serial ? `<td>${d.serial_no || ""}</td>` : ""}
				${show_batch ? `<td>${d.batch_no || ""}</td>` : ""}
				<td style="text-align: right;">${
					!d.serial_no && show_batch ? this.get_qty_input(d) : this.format_float(Math.abs(d.qty))
				}</td>
			</tr>`
			)
			.join("");

		if (!entries.length) {
			body = `<tr class="sbie-empty"><td colspan="${column_count}" style="text-align: center;">
				${__("Scan or type serial / batch numbers above and click Add")}</td></tr>`;
		}

		this.wrapper.find(".sbie-table").html(`<table>${header}<tbody>${body}</tbody></table>`);

		this.wrapper.find(".sbie-check-all").on("change", (e) => {
			this.wrapper.find(".sbie-check").prop("checked", e.target.checked);
			this.toggle_delete_button();
		});
		this.wrapper.find(".sbie-check").on("change", () => this.toggle_delete_button());
		this.wrapper.find(".sbie-qty-input").on("input", (e) => this.restrict_to_numeric(e));
		this.wrapper.find(".sbie-qty-input").on("blur", (e) => this.apply_float_format(e));
		this.wrapper.find(".sbie-qty-input").on("change", (e) => this.update_qty(e));
		this.wrapper.find(".sbie-qty-input").on("focus", (e) => e.target.select());
	}

	get_qty_input(d) {
		return `<input type="text" class="form-control input-xs sbie-qty-input" data-fieldtype="Float"
			data-name="${d.name}" value="${this.format_float(Math.abs(d.qty))}"
			style="width: 90px; display: block; margin-left: auto; text-align: right;">`;
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
		this.wrapper.find(".sbie-delete").toggleClass("hidden", !checked);
	}

	update_summary(data) {
		this.total_count = data.total_count;
		this.wrapper
			.find(".sbie-summary")
			.text(__("Total Qty: {0} ({1} entries)", [data.total_qty, data.total_count]));

		let page_end = Math.min(this.start + this.page_length, data.total_count);
		this.wrapper
			.find(".sbie-page-info")
			.text(data.total_count ? `${this.start + 1}-${page_end} / ${data.total_count}` : "");
	}

	add_entries() {
		let entries = this.collect_new_entries();
		if (!entries.length) return;

		if (this.is_rejected && !this.row.rejected_warehouse) {
			frappe.msgprint(__("Please set Rejected Warehouse first"));
			return;
		}

		this.upsert({ entries });
		this.wrapper.find(".sbie-qty").val("");
		this.serial_control && this.serial_control.set_value("");
		this.batch_control && this.batch_control.set_value("");
	}

	collect_new_entries() {
		let serials = (this.serial_control ? this.serial_control.get_value() || "" : "")
			.split(/[\n,]/)
			.map((d) => d.trim())
			.filter(Boolean);
		let batch_no = this.batch_control ? this.batch_control.get_value() : "";
		let qty = flt(this.wrapper.find(".sbie-qty").val()) || 1;

		if (serials.length) {
			return serials.map((serial_no) => ({ serial_no, batch_no, qty: 1 }));
		}

		if (batch_no) {
			return [{ batch_no, qty }];
		}

		return [];
	}

	update_qty(e) {
		let $input = $(e.target);
		this.upsert({
			entries: [{ name: $input.data("name"), qty: flt($input.val()) || 1 }],
		});
	}

	delete_selected() {
		let deleted = this.wrapper
			.find(".sbie-check:checked")
			.map((_, el) => $(el).data("name"))
			.get();

		if (deleted.length) {
			this.upsert({ deleted });
		}
	}

	async upsert({ entries = [], deleted = [], replace = 0 }) {
		let summary = await this.call(
			"erpnext.stock.doctype.serial_and_batch_bundle.inline_editor.upsert_bundle_entries",
			{
				child_row: Object.assign({}, this.row, { is_rejected: this.is_rejected }),
				doc: this.frm.doc,
				entries: entries,
				deleted: deleted,
				replace: replace,
			}
		);

		if (this.bundle !== summary.bundle) {
			await frappe.model.set_value(this.cdt, this.cdn, this.bundle_field, summary.bundle);
		}
		await frappe.model.set_value(this.cdt, this.cdn, this.qty_field, summary.total_qty);

		this.load_page();
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

erpnext.stock.mount_serial_batch_inline_editor = async function (frm, cdt, cdn) {
	let grid_row = frm.fields_dict.items.grid.grid_rows_by_docname[cdn];
	let grid_form = grid_row && grid_row.grid_form;
	if (!grid_form) return;

	let editors = [
		{ fieldname: "serial_batch_entries_html", is_rejected: 0 },
		{ fieldname: "rejected_serial_batch_entries_html", is_rejected: 1 },
	];

	let enabled = await erpnext.stock.is_inline_serial_batch_editor_enabled();
	let row = locals[cdt][cdn];
	let show = enabled && row && !row.use_serial_batch_fields && frm.doc.docstatus === 0;

	erpnext.stock.toggle_legacy_bundle_fields(grid_form, show);

	for (let editor of editors) {
		let field = grid_form.fields_dict[editor.fieldname];
		if (!field) continue;

		if (!show) {
			field.$wrapper.closest(".form-section").hide();
			continue;
		}

		new erpnext.stock.SerialBatchInlineEditor({
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
		"serial_and_batch_bundle",
		"add_serial_batch_for_rejected_qty",
		"rejected_serial_and_batch_bundle",
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

erpnext.stock.is_inline_serial_batch_editor_enabled = async function () {
	if (erpnext.stock._inline_editor_enabled === undefined) {
		let { message } = await frappe.db.get_value(
			"Stock Settings",
			"Stock Settings",
			"use_inline_serial_batch_editor"
		);
		erpnext.stock._inline_editor_enabled = cint(message && message.use_inline_serial_batch_editor);
	}

	return erpnext.stock._inline_editor_enabled;
};
