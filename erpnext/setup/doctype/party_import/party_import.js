class PartyDataExporter {
	constructor(frm) {
		this.frm = frm;
		this.party_type = frm.doc.party_type;
		this.docname = frm.doc.name;
		this.party_doctype = this.party_type === "Supplier" ? "Supplier" : "Customer";
		this.doctypes = [this.party_doctype, "Address", "Contact"];
		this.checked = {};
		this.mandatory_set = new Set();
		this.party_mandatory_set = new Set();
		this.active_subsections = {};
		this._load_metas();
	}

	_load_metas() {
		let loaded = 0;
		this.doctypes.forEach((dt) => {
			frappe.model.with_doctype(dt, () => {
				loaded++;
				if (loaded === this.doctypes.length) this._fetch_fields();
			});
		});
	}

	_fetch_fields() {
		frappe.call({
			method: "erpnext.setup.doctype.party_import.party_import.get_template_fields",
			args: { docname: this.docname, party_type: this.party_type },
			freeze: true,
			freeze_message: __("Loading fields…"),
			callback: (r) => {
				if (r.exc || !r.message) return;
				this.sections = r.message.sections;
				this.mandatory_set = new Set(r.message.mandatory_fieldnames);
				this.party_mandatory_set = new Set(r.message.party_mandatory_fieldnames);
				this.sections.forEach((s) => {
					const is_party = s.doctype !== "Address" && s.doctype !== "Contact";
					s.fields.forEach((f) => {
						this.checked[`${s.doctype}::${f.fieldname}`] =
							is_party && this.party_mandatory_set.has(f.fieldname);
					});
					(s.subsections || []).forEach((sub) => {
						sub.fields.forEach((f) => {
							this.checked[`${sub.doctype}::${f.fieldname}`] = false;
						});
						this.active_subsections[sub.doctype] = false;
					});
				});
				this._make_dialog();
			},
		});
	}

	_make_dialog() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Download Import Template"),
			fields: [
				{
					fieldtype: "Select",
					fieldname: "export_type",
					label: __("Export Type"),
					options: [
						{ value: "blank_template", label: __("Blank Template") },
						{ value: "5_records", label: __("5 Records") },
						{ value: "all_records", label: __("All Records") },
					],
					default: "blank_template",
					onchange: () => this._update_record_count(),
				},
				{
					fieldtype: "HTML",
					fieldname: "record_count_msg",
					options: `<p id="pit-record-count"
                        style="font-size:12px;color:var(--text-muted);
                        margin:0 0 4px">
                        ${__("No records will be exported.")}
                    </p>`,
				},
				{
					fieldtype: "Select",
					fieldname: "file_type",
					label: __("File Format"),
					options: "xlsx\ncsv",
					default: "xlsx",
				},
				{
					fieldtype: "Check",
					fieldname: "multi_emails_phones",
					label: __("Allow multiple emails / phones per contact"),
					description: __(
						"When on, the template uses the Contact Email and Contact Phone subsection columns instead of the single Email Address / Phone fields on Contact."
					),
					default: 0,
					onchange: () => this._on_multi_mode_change(),
				},
				{
					fieldtype: "HTML",
					fieldname: "action_btns",
					options: `
                        <p class="form-label" style="
                            font-size:11px;font-weight:600;
                            text-transform:uppercase;
                            letter-spacing:.05em;
                            color:var(--text-muted);
                            margin-bottom:8px;margin-top:4px">
                            ${__("Select Fields to Insert")}
                        </p>
                        <div style="display:flex;gap:8px;
                            margin-bottom:10px;flex-wrap:wrap">
                            <button class="btn btn-xs btn-default"
                                id="pit-select-all">${__("Select All")}</button>
                            <button class="btn btn-xs btn-default"
                                id="pit-select-mandatory">${__("Select Mandatory")}</button>
                            <button class="btn btn-xs btn-default"
                                id="pit-unselect-all">${__("Unselect All")}</button>
                        </div>`,
				},
				{
					fieldtype: "Data",
					fieldname: "search",
					placeholder: __("Search"),
				},
				{
					fieldtype: "HTML",
					fieldname: "fields_html",
					options: `<div id="pit-fields-body"
                        style="max-height:400px;overflow-y:auto;
                        padding-right:4px"></div>`,
				},
			],
			primary_action_label: __("Download"),
			primary_action: () => this._on_download(),
			size: "large",
		});

		this.dialog.show();
		this._render_fields("");
		this._bind_controls();
		this._update_record_count();
	}
	_is_multi_mode() {
		return !!(this.dialog && this.dialog.get_value && this.dialog.get_value("multi_emails_phones"));
	}

	_is_contact_bare_email_or_phone(doctype, fieldname) {
		return doctype === "Contact" && (fieldname === "email_id" || fieldname === "phone");
	}

	_is_contact_subsection(doctype) {
		return doctype === "Contact Email" || doctype === "Contact Phone";
	}

	_field_hidden_by_mode(doctype, fieldname) {
		const multi = this._is_multi_mode();
		if (multi && this._is_contact_bare_email_or_phone(doctype, fieldname)) return true;
		if (!multi && this._is_contact_subsection(doctype)) return true;
		return false;
	}

	_on_multi_mode_change() {
		const multi = this._is_multi_mode();
		this.sections.forEach((s) => {
			if (s.doctype === "Contact") {
				s.fields.forEach((f) => {
					if (this._is_contact_bare_email_or_phone(s.doctype, f.fieldname) && multi) {
						this.checked[`${s.doctype}::${f.fieldname}`] = false;
					}
				});
			}
			(s.subsections || []).forEach((sub) => {
				if (!this._is_contact_subsection(sub.doctype)) return;
				this.active_subsections[sub.doctype] = multi;
				sub.fields.forEach((f) => {
					this.checked[`${sub.doctype}::${f.fieldname}`] = multi && !!f.reqd;
				});
			});
		});
		this._render_fields(this.dialog.get_value("search") || "");
	}

	_on_download() {
		const selected = [];
		const file_type = this.dialog.get_value("file_type") || "xlsx";
		const export_type = this.dialog.get_value("export_type") || "blank_template";

		this.sections.forEach((s) => {
			s.fields.forEach((f) => {
				if (this._field_hidden_by_mode(s.doctype, f.fieldname)) return;
				if (
					this.party_mandatory_set.has(f.fieldname) ||
					this.checked[`${s.doctype}::${f.fieldname}`]
				) {
					selected.push({ doctype: s.doctype, fieldname: f.fieldname, label: f.label });
				}
			});
			(s.subsections || []).forEach((sub) => {
				if (this._field_hidden_by_mode(sub.doctype, null)) return;
				sub.fields.forEach((f) => {
					if (this.checked[`${sub.doctype}::${f.fieldname}`]) {
						selected.push({
							doctype: sub.doctype,
							fieldname: f.fieldname,
							label: f.label,
							parent_field: sub.parent_field,
							is_child: true,
						});
					}
				});
			});
		});

		this.dialog.hide();

		open_url_post(frappe.request.url, {
			cmd: "erpnext.setup.doctype.party_import.party_import.download_template",
			docname: this.docname,
			party_type: this.party_type,
			fields: JSON.stringify(selected),
			file_type: file_type,
			export_type: export_type,
		});
	}
	_update_record_count() {
		const me = this;
		const export_type = this.dialog.get_value("export_type");
		const $msg = this.dialog.$wrapper.find("#pit-record-count");

		if (export_type === "blank_template") {
			$msg.text(__("No records will be exported."));
			return;
		}

		frappe.call({
			method: "erpnext.setup.doctype.party_import.party_import.get_party_count",
			args: {
				docname: me.docname,
				party_type: me.party_type,
			},
			callback(r) {
				if (r.exc || r.message === undefined) return;
				const total = r.message;
				const shown = export_type === "5_records" ? Math.min(5, total) : total;
				$msg.text(__("{0} of {1} {2}(s) will be exported.", [shown, total, me.party_doctype]));
			},
		});
	}
	_render_fields(filter) {
		const q = (filter || "").toLowerCase();
		let html = "";

		this.sections.forEach((s) => {
			const visible_parent = s.fields.filter(
				(f) =>
					!this._field_hidden_by_mode(s.doctype, f.fieldname) &&
					(!q || f.label.toLowerCase().includes(q) || f.fieldname.toLowerCase().includes(q))
			);
			const visible_subsections = (s.subsections || [])
				.filter((sub) => !this._field_hidden_by_mode(sub.doctype, null))
				.map((sub) => ({
					...sub,
					fields: sub.fields.filter(
						(f) =>
							!q ||
							sub.label.toLowerCase().includes(q) ||
							f.label.toLowerCase().includes(q) ||
							f.fieldname.toLowerCase().includes(q)
					),
				}))
				.filter((sub) => sub.fields.length > 0);

			if (!visible_parent.length && !visible_subsections.length) return;

			html += `<div style="margin-bottom:20px">
				<div style="font-size:13px;font-weight:600;
					color:var(--text-color);margin-bottom:8px">
					${__(s.label)}
				</div>`;

			if (visible_parent.length) {
				html += `<div style="display:grid;grid-template-columns:1fr 1fr;
					gap:0 16px;margin-bottom:8px">`;
				visible_parent.forEach((f) => {
					html += this._field_html(s.doctype, f, false);
				});
				html += `</div>`;
			}

			visible_subsections.forEach((sub) => {
				const is_active = !!this.active_subsections[sub.doctype];
				html += `
					<div style="margin-top:10px;margin-left:16px;
						padding-left:12px;
						border-left:2px solid var(--border-color)">
						<div style="font-size:11px;font-weight:600;
							letter-spacing:.04em;color:var(--text-muted);
							margin-bottom:4px">
							${__(sub.label)}
						</div>`;
				html += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">`;
				sub.fields.forEach((f) => {
					html += this._field_html(sub.doctype, f, is_active && !!f.reqd);
				});
				html += `</div></div>`;
			});

			html += `</div>`;
		});

		if (!html) html = `<p style="color:var(--text-muted);font-size:13px">${__("No fields match.")}</p>`;

		this.dialog.$wrapper.find("#pit-fields-body").html(html);
		this._bind_checkboxes();
	}

	_field_html(doctype, f, force_locked) {
		const key = `${doctype}::${f.fieldname}`;
		const is_reqd = this.mandatory_set.has(f.fieldname);
		const is_child_reqd = !!f.reqd;
		const locked = this.party_mandatory_set.has(f.fieldname) || force_locked;
		const is_dep = !is_reqd && !is_child_reqd && !!f.depends_on;
		const is_chk = this.checked[key] === true;
		const color =
			is_reqd || is_child_reqd
				? "var(--red-500,#c0392b)"
				: is_dep
				? "var(--orange-500,#e67e22)"
				: "var(--text-color)";

		return `
			<label style="display:flex;align-items:center;gap:6px;
				padding:4px 2px;cursor:${locked ? "default" : "pointer"}">
				<input type="checkbox"
					data-key="${key}"
					data-doctype="${frappe.utils.escape_html(doctype)}"
					data-fieldname="${frappe.utils.escape_html(f.fieldname)}"
					data-label="${frappe.utils.escape_html(f.label)}"
					data-child-reqd="${is_child_reqd ? 1 : 0}"
					${is_chk ? "checked" : ""} ${locked ? "disabled" : ""}
					style="flex-shrink:0;cursor:${locked ? "default" : "pointer"}">
				<span style="font-size:12px;color:${color}">
					${frappe.utils.escape_html(f.label)}
				</span>
			</label>`;
	}

	_bind_checkboxes() {
		this.dialog.$wrapper
			.find("#pit-fields-body input[type=checkbox]:not([disabled])")
			.off("change")
			.on("change", (e) => {
				const $cb = $(e.target);
				const key = $cb.data("key");
				const doctype = $cb.data("doctype");
				this.checked[key] = e.target.checked;
				const sub = this._find_subsection(doctype);
				if (!sub) return;
				const any_checked = sub.fields.some((f) => this.checked[`${sub.doctype}::${f.fieldname}`]);
				const was_active = this.active_subsections[sub.doctype];
				this.active_subsections[sub.doctype] = any_checked;
				if (any_checked !== was_active) {
					sub.fields.forEach((f) => {
						if (f.reqd) this.checked[`${sub.doctype}::${f.fieldname}`] = any_checked;
					});
					this._render_fields(this.dialog.get_value("search") || "");
				}
			});
	}

	_find_subsection(doctype) {
		for (const s of this.sections) {
			for (const sub of s.subsections || []) {
				if (sub.doctype === doctype) return sub;
			}
		}
		return null;
	}

	_bind_controls() {
		const $d = this.dialog.$wrapper;
		const current_filter = () => this.dialog.get_value("search") || "";

		this.dialog.fields_dict.search.$input.on("input", (e) => {
			this._render_fields($(e.target).val());
		});
		$d.find("#pit-select-all").on("click", () => {
			this.sections.forEach((s) => {
				s.fields.forEach((f) => {
					const hidden = this._field_hidden_by_mode(s.doctype, f.fieldname);
					this.checked[`${s.doctype}::${f.fieldname}`] = !hidden;
				});
				(s.subsections || []).forEach((sub) => {
					const hidden = this._field_hidden_by_mode(sub.doctype, null);
					this.active_subsections[sub.doctype] = !hidden;
					sub.fields.forEach((f) => (this.checked[`${sub.doctype}::${f.fieldname}`] = !hidden));
				});
			});
			this._render_fields(current_filter());
		});
		$d.find("#pit-select-mandatory").on("click", () => {
			this.sections.forEach((s) => {
				s.fields.forEach((f) => {
					const hidden = this._field_hidden_by_mode(s.doctype, f.fieldname);
					this.checked[`${s.doctype}::${f.fieldname}`] =
						!hidden && this.mandatory_set.has(f.fieldname);
				});
				(s.subsections || []).forEach((sub) => {
					sub.fields.forEach((f) => (this.checked[`${sub.doctype}::${f.fieldname}`] = false));
					this.active_subsections[sub.doctype] = false;
				});
			});
			this._render_fields(current_filter());
		});
		$d.find("#pit-unselect-all").on("click", () => {
			this.sections.forEach((s) => {
				s.fields.forEach((f) => {
					if (!this.party_mandatory_set.has(f.fieldname))
						this.checked[`${s.doctype}::${f.fieldname}`] = false;
				});
				(s.subsections || []).forEach((sub) => {
					sub.fields.forEach((f) => (this.checked[`${sub.doctype}::${f.fieldname}`] = false));
					this.active_subsections[sub.doctype] = false;
				});
			});
			this._render_fields(current_filter());
		});
	}
}

frappe.ui.form.on("Party Import", {
	setup(frm) {
		frm.set_query("default_customer_group", () => ({ filters: { is_group: 0 } }));
		frm.set_query("default_supplier_group", () => ({ filters: { is_group: 0 } }));
		frm.set_query("default_territory", () => ({ filters: { is_group: 0 } }));
		frm.trigger("update_primary_action");
	},

	refresh(frm) {
		frm.trigger("update_primary_action");
		frm.trigger("setup_realtime");

		if (frm.doc.import_log && frm.doc.import_log.length) {
			frm.trigger("render_log_summary");
		}

		if (frm.doc.status === "Pending") {
			frm.dashboard.show_progress(__("Importing…"), 1, __("Starting…"));
		} else {
			frm.dashboard.hide_progress(__("Importing…"));
		}
	},

	onload_post_render(frm) {
		frm.trigger("update_primary_action");
	},

	update_primary_action(frm) {
		if (frm.is_dirty()) {
			frm.enable_save();
			return;
		}

		frm.disable_save();
		frm.page.clear_inner_toolbar();

		if (frm.doc.status !== "Success") {
			if (!frm.is_new() && frm.doc.import_file) {
				const label =
					frm.doc.status === "Pending"
						? __("Importing…")
						: frm.doc.status === "Draft"
						? __("Start Import")
						: __("Retry");

				frm.page.set_primary_action(
					label,
					() => {
						frm.trigger("confirm_and_import");
					},
					"upload"
				);

				if (frm.doc.status === "Pending") {
					if (frm.page.btn_primary) {
						frm.page.btn_primary.prop("disabled", true);
					}

					frm.page.add_inner_button(__("Stop Import"), () => {
						frm.trigger("stop_import");
					});
				}
			} else {
				frm.page.set_primary_action(__("Save"), () => frm.save());
			}
		}

		const has_errors = frm.doc.failed_count > 0;
		const can_export = ["Partial Success", "Error"].includes(frm.doc.status);

		if (!frm.is_new() && has_errors && can_export) {
			frm.page.add_inner_button(__("Download Errored Rows"), () => {
				frm.trigger("export_errored_rows");
			});
		}
	},

	import_file(frm) {
		frm.trigger("update_primary_action");
	},
	status(frm) {
		frm.trigger("update_primary_action");
	},

	default_customer_group(frm) {
		frm.trigger("update_primary_action");
	},
	default_supplier_group(frm) {
		frm.trigger("update_primary_action");
	},
	default_territory(frm) {
		frm.trigger("update_primary_action");
	},
	default_address_type(frm) {
		frm.trigger("update_primary_action");
	},
	create_customer_group(frm) {
		frm.trigger("update_primary_action");
	},
	create_supplier_group(frm) {
		frm.trigger("update_primary_action");
	},
	create_territory(frm) {
		frm.trigger("update_primary_action");
	},

	setup_realtime(frm) {
		frappe.realtime.off("party_import_progress");
		frappe.realtime.off("party_import_refresh");

		frappe.realtime.on("party_import_progress", (data) => {
			if (data.party_import !== frm.doc.name) return;
			const pct = data.total ? Math.max(1, Math.round((data.processed / data.total) * 100)) : 1;
			const description = __("{0} of {1} — {2} success, {3} failed", [
				data.processed,
				data.total,
				data.success,
				data.failed,
			]);
			frm.dashboard.show_progress(__("Importing…"), pct, description);
		});

		frappe.realtime.on("party_import_refresh", (data) => {
			if (data.party_import !== frm.doc.name) return;
			frm.reload_doc().then(() => {
				const status = frm.doc.status;
				const indicator =
					{ Success: "green", "Partial Success": "orange", Error: "red" }[status] || "gray";
				frappe.show_alert(
					{
						message: __("Import {0} — {1} succeeded, {2} failed", [
							status,
							frm.doc.success_count || 0,
							frm.doc.failed_count || 0,
						]),
						indicator,
					},
					7
				);
			});
		});
	},

	confirm_and_import(frm) {
		if (frm.doc.status === "Pending") return;

		const label = frm.doc.party_type === "Supplier" ? __("Suppliers") : __("Customers");

		frappe.confirm(
			__("This will create {0}, Addresses and Contacts from the attached file. Continue?", [label]),
			() => {
				frappe.call({
					method: "start_import",
					doc: frm.doc,
					callback(r) {
						if (r.exc) return;
						if (r.message === false) return;
						frm.doc.status = "Pending";
						frm.trigger("update_primary_action");
						frm.dashboard.show_progress(__("Importing…"), 1, __("Starting…"));
					},
				});
			}
		);
	},

	stop_import(frm) {
		frappe.confirm(__("Stop the running import? Rows processed so far will be kept."), () => {
			frappe.call({
				method: "erpnext.setup.doctype.party_import.party_import.stop_import",
				args: { party_import: frm.doc.name },
				callback(r) {
					if (r.exc) return;
					frappe.show_alert({ message: __("Import stopped"), indicator: "orange" });
					frm.reload_doc();
				},
			});
		});
	},

	export_errored_rows(frm) {
		open_url_post(frappe.request.url, {
			cmd: "erpnext.setup.doctype.party_import.party_import.export_errored_rows",
			docname: frm.doc.name,
		});
	},

	download_template(frm) {
		if (!frm.doc.party_type) {
			frappe.msgprint({ message: __("Select a Party Type first."), indicator: "orange" });
			return;
		}
		new PartyDataExporter(frm);
	},

	render_log_summary(frm) {
		const wrapper = frm.get_field("import_log_html") && frm.get_field("import_log_html").$wrapper;
		if (!wrapper) return;

		if (!frm.doc.import_log || !frm.doc.import_log.length) {
			wrapper.empty();
			return;
		}

		const rows = frm.doc.import_log;
		const counts = { Success: 0, Skipped: 0, Error: 0 };
		const pill_color = { Success: "green", Skipped: "orange", Error: "red" };

		rows.forEach((r) => {
			if (counts[r.status] !== undefined) counts[r.status]++;
		});

		const badges = Object.entries(counts)
			.map(
				([s, n]) =>
					`<span class="indicator-pill ${pill_color[s]}"
				style="margin-right:8px;font-size:12px">
				${n} ${__(s)}
			</span>`
			)
			.join("");

		const party_type = frm.doc.party_type;
		const party_link = (r) => {
			const code = r.party_code || "";
			if (!code) return "";
			const target = r.docname || code;
			if (!party_type || !r.docname) {
				return `<code style="font-size:11px">${frappe.utils.escape_html(code)}</code>`;
			}
			const href = frappe.utils.get_form_link(party_type, target);
			return `<a href="${href}" data-doctype="${frappe.utils.escape_html(party_type)}"
				data-name="${frappe.utils.escape_html(target)}"
				style="font-family:var(--font-stack-monospace);font-size:11px">
				${frappe.utils.escape_html(code)}
			</a>`;
		};

		const tbody = rows
			.map(
				(r) => `
			<tr>
				<td>${r.row_index}</td>
				<td>${party_link(r)}</td>
				<td>${frappe.utils.escape_html(r.party_name || "")}</td>
				<td>
					<span class="indicator-pill ${pill_color[r.status] || "gray"}"
						style="font-size:11px">${__(r.status)}</span>
				</td>
				<td style="text-align:center">${r.party_created ? "✓" : ""}</td>
				<td style="text-align:center">${r.address_created ? "✓" : ""}</td>
				<td style="text-align:center">${r.contact_created ? "✓" : ""}</td>
				<td style="color:var(--text-muted,#888);font-size:11px">
					${frappe.utils.escape_html(r.message || "")}
				</td>
			</tr>`
			)
			.join("");

		const html = `
			<div style="margin-bottom:10px">${badges}</div>
			<div style="overflow-x:auto;max-height:380px;overflow-y:auto">
				<table class="table table-bordered table-condensed" style="font-size:12px">
					<thead style="position:sticky;top:0;background:var(--bg-light-gray,#f4f4f4)">
						<tr>
							<th>${__("Row")}</th><th>${__("Code")}</th>
							<th>${__("Name")}</th><th>${__("Status")}</th>
							<th>${__("Party")}</th><th>${__("Address")}</th>
							<th>${__("Contact")}</th><th>${__("Message")}</th>
						</tr>
					</thead>
					<tbody>${tbody}</tbody>
				</table>
			</div>`;

		wrapper.html(html);
	},
});
