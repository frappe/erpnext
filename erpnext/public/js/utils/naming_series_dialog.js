frappe.provide("erpnext");

erpnext.NamingSeriesDialog = class NamingSeriesDialog {
	constructor(opts = {}) {
		this.opts = Object.assign(
			{
				title: __("Document Naming"),
				single_doctype: "Document Naming Settings",
			},
			opts
		);

		this.current_doctype = null;
		this.loaded = false;
		this.make_dialog();
	}

	make_dialog() {
		this.dialog = new frappe.ui.Dialog({
			title: this.opts.title,
			size: "medium",
			fields: [
				{
					fieldtype: "Table",
					fieldname: "naming_series_options",
					label: __("Add Series Prefix"),
					reqd: 1,
					in_place_edit: true,
					data: [],
					fields: [
						{
							fieldtype: "Data",
							fieldname: "series",
							label: __("Series"),
							in_list_view: 1,
							change: async function () {
								const preview = await this.grid_row.grid._naming_dialog.get_series_preview(
									this.doc.series
								);
								this.doc.preview = preview;
								this.grid_row.refresh_field("preview");
							},
						},
						{
							fieldtype: "Data",
							fieldname: "preview",
							label: __("Preview"),
							in_list_view: 1,
							placeholder: " ",
							read_only: 1,
						},
					],
				},
				{ fieldtype: "Section Break", label: __("Rules for configuring series"), collapsible: 1 },
				{
					fieldtype: "HTML",
					fieldname: "naming_series_description",
				},
			],
			primary_action_label: __("Update"),
			primary_action: () => this.save(),
		});

		this.dialog.fields_dict.naming_series_options.grid._naming_dialog = this;
	}

	async show() {
		this.dialog.show();
		this.render_help();

		if (this.opts.doctype && !this.loaded) {
			await this.get_transaction(this.opts.doctype);
			this.loaded = true;
			return;
		}
	}

	render_help() {
		this.dialog.get_field("naming_series_description").$wrapper.html(`
   			 <ul>
				<li>${__("Allowed special characters are '/' and '-'")}</li>
				<li>
					${__(
						"Optionally, set the number of digits in the series using dot (.) followed by hashes (#). For example, '.####' means that the series will have four digits. Default is five digits."
					)}
				</li>
        	<li> ${__("You can also use variables in the series name by putting them between (.) dots")}
            <br>
            ${__("Supported Variables:")}
				<ul>
					<li><code>.YYYY.</code> - ${__("Year in 4 digits")}</li>
					<li><code>.YY.</code> - ${__("Year in 2 digits")}</li>
					<li><code>.MM.</code> - ${__("Month")}</li>
					<li><code>.DD.</code> - ${__("Day of month")}</li>
					<li><code>.WW.</code> - ${__("Week of the year")}</li>
					<li>
						<code>.{fieldname}.</code> - ${__("fieldname on the document e.g.")}
						<code>branch</code>
					</li>
					<li><code>.FY.</code> - ${__("Fiscal Year (requires ERPNext to be installed)")}</li>
					<li><code>.ABBR.</code> - ${__("Company Abbreviation (requires ERPNext to be installed)")}</li>
				</ul>
       		</li>
    		</ul>
    Examples:
    <ul>
        <li>INV-</li>
        <li>INV-10-</li>
        <li>INVK-</li>
        <li>INV-.YYYY.-._{branch}.-.MM.-.####</li>
    </ul>
	<br>`);
	}

	get_series_preview(series) {
		if (!series) return "";

		return this.get_document_naming_doc().then((doc) => {
			doc.try_naming_series = series;
			doc.transaction_type = this.current_doctype;
			return frappe
				.call({
					doc: doc,
					method: "preview_series",
					freeze: true,
				})
				.then((r) => (r.message || "").split("\n")[0] || "");
		});
	}

	get_document_naming_doc() {
		const dt = this.opts.single_doctype;
		return frappe.model.with_doc(dt, dt).then(() => {
			return frappe.model.get_doc(dt, dt);
		});
	}

	async get_transaction(doctype) {
		this.current_doctype = doctype;

		await frappe.model.with_doctype(doctype, async () => {
			const meta = frappe.get_meta(doctype);
			const naming_df = (meta?.fields || []).find((df) => df.fieldname === "naming_series");
			const series_list = (naming_df?.options || "").split("\n").filter(Boolean);
			const rows = await Promise.all(
				series_list.map(async (series) => ({
					series: series,
					preview: await this.get_series_preview(series),
				}))
			);

			this.dialog.fields_dict.naming_series_options.df.data = rows;
			this.dialog.fields_dict.naming_series_options.grid.refresh();
		});
	}

	save() {
		const rows = this.dialog.fields_dict.naming_series_options.grid.get_data();
		const naming_series_options = rows
			.map((r) => (r.series || "").trim())
			.filter(Boolean)
			.join("\n");

		if (!this.current_doctype) {
			frappe.msgprint(__("Please select a transaction."));
			return;
		}

		if (!naming_series_options) {
			frappe.msgprint(__("Please add at least one naming series."));
			return;
		}

		this.get_document_naming_doc().then((doc) => {
			doc.transaction_type = this.current_doctype;
			doc.naming_series_options = naming_series_options;

			frappe.call({
				doc: doc,
				method: "update_series",
				freeze: true,
				callback: async () => {
					const updated_rows = await Promise.all(
						naming_series_options
							.split("\n")
							.filter(Boolean)
							.map(async (series) => ({
								series: series,
								preview: await this.get_series_preview(series),
							}))
					);

					this.dialog.fields_dict.naming_series_options.df.data = updated_rows;
					this.dialog.fields_dict.naming_series_options.grid.refresh();

					frappe.show_alert({ message: __("Naming Series updated"), indicator: "green" });
					this.dialog.hide();
					this.opts.on_update?.({ doctype: this.current_doctype, naming_series_options });
				},
			});
		});
	}
};

erpnext.NamingSeriesTable = class NamingSeriesTable {
	constructor(opts = {}) {
		this.frm = opts.frm;
		this.transactions = opts.transactions || [];
		this.$wrapper = opts.frm.get_field(opts.fieldname).$wrapper;
	}
	render() {
		this.$wrapper.html(`
			<div class="form-grid" style="margin-bottom: 24px;">
				<table class="table" style="margin: 0;">
					<thead class="grid-heading-row" style="background-color: var(--subtle-fg);">
						<tr>
							<td style="width: 25%; padding: 8px 12px; text-align: left;">
								${__("Transaction")}
							</td>
							<td colspan="2"
								style="width: 75%; padding: 8px 12px; text-align: left; border-left: 1px solid var(--border-color);">
								${__("Current Series")}
							</td>
						</tr>
					</thead>
					<tbody class="naming-series-table-rows"></tbody>
				</table>
			</div>
    `);

		const $rows = this.$wrapper.find(".naming-series-table-rows");
		this.map_configure_button($rows);
		this.get_row_data($rows);
	}

	map_configure_button($rows) {
		$rows.on("click", ".configure-btn", (e) => {
			const $btn = $(e.currentTarget);
			const doctype = $btn.data("doctype");
			const label = $btn.data("label");

			if (!this.frm._naming_dialogs) this.frm._naming_dialogs = {};

			if (!this.frm._naming_dialogs[doctype]) {
				this.frm._naming_dialogs[doctype] = new erpnext.NamingSeriesDialog({
					doctype: doctype,
					title: __("{0} Naming Series", [__(label)]),
					on_update: ({ naming_series_options }) => {
						const series = naming_series_options.split("\n").filter(Boolean);
						this.$wrapper
							.find(`.series-cell-${frappe.scrub(doctype)}`)
							.html(this.series_list_background(series));
					},
				});
			}

			this.frm._naming_dialogs[doctype].show();
		});
	}

	get_row_data($rows) {
		this.transactions.forEach((t) => {
			frappe.model.with_doctype(t.doctype, () => {
				const meta = frappe.get_meta(t.doctype);
				const naming_df = (meta?.fields || []).find((df) => df.fieldname === "naming_series");
				const series = (naming_df?.options || "")
					.split("\n")
					.map((s) => s.trim())
					.filter(Boolean);

				$rows.append(this.make_row(t, series));
			});
		});
	}

	make_row(t, series) {
		return $(`
        <tr>
            <td style="width: 25%; padding: 8px 12px; vertical-align: top; background-color: var(--card-bg);">
                ${frappe.utils.escape_html(t.label)}
            </td>
            <td class="series-cell-${frappe.scrub(t.doctype)}"
                style="width: 70%; padding: 8px 12px; border-left: 1px solid var(--border-color); white-space: normal; vertical-align: top; background-color: var(--card-bg);">
                ${this.series_list_background(series)}
            </td>
            <td class="text-center"
                style="width: 5%; padding: 8px 12px; border-left: 1px solid var(--border-color); vertical-align: middle; background-color: var(--card-bg);">
                <a class="btn-link configure-btn"
                    data-doctype="${frappe.utils.escape_html(t.doctype)}"
                    data-label="${frappe.utils.escape_html(t.label)}"
                    style="cursor: pointer; color: var(--text-muted);">
                    ${frappe.utils.icon("edit", "sm")}
                </a>
            </td>
        </tr>
    `);
	}

	series_list_background(series_list) {
		if (!series_list.length) {
			return `<span class="text-muted">${__("Not configured")}</span>`;
		}
		return series_list
			.map(
				(s) => `<span class="badge badge-light"
					style="margin: 2px; font-family: monospace; font-weight: normal;">
					${frappe.utils.escape_html(s)}
				</span>`
			)
			.join("");
	}
};
