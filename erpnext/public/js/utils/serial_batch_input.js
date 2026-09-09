// Physical input remains pending until the transaction is saved.
const registered_forms = new Set();
const pending_values = new WeakMap();
const serial_list_fields = new Set(["serial_no", "rejected_serial_no", "current_serial_no"]);

const with_serial_numbers = (BaseControl) =>
	class extends BaseControl {
		number_context() {
			return this.serial_batch_context || { frm: this.frm, row: this.doc };
		}

		is_serial_list() {
			const { frm, row } = this.number_context();
			return (
				frm &&
				this.df.parent !== "Serial No" &&
				serial_list_fields.has(this.df.fieldname) &&
				(row?.item_code || row?.rm_item_code)
			);
		}

		bind_change_event() {
			if (!this.frm || !serial_list_fields.has(this.df.fieldname) || this.df.parent === "Serial No")
				return super.bind_change_event();
			this.$input.on("change", (event) =>
				this.parse_validate_and_set_in_model(this.get_input_value(), event)
			);
			this.$input.on("input", () => this.number_context().frm.dirty());
		}

		async parse_validate_and_set_in_model(value, event) {
			const revision = (this.number_revision = (this.number_revision || 0) + 1);
			if (!this.is_serial_list() || !event) {
				return super.parse_validate_and_set_in_model(value, event);
			}
			const context = this.number_context();
			if (
				context.row.parenttype &&
				frappe.meta.has_field(context.row.doctype, "serial_and_batch_bundle")
			) {
				const numbers = split_physical_numbers(value);
				await set_pending_number(context, this.df.fieldname, numbers.join("\n"));
				return;
			}
			const { frm, row } = this.number_context();
			const item_code = row.item_code || row.rm_item_code;
			const pending = (async () => {
				const numbers = (value || "")
					.split(/[,\n]/)
					.map((number) => number.trim())
					.filter(Boolean);
				const result = numbers.length
					? await frappe.xcall("erpnext.stock.serial_batch_identity.resolve_serial_batch_numbers", {
							item_code,
							serial_numbers: numbers,
					  })
					: { serial_nos: [] };
				const ids = result.serial_nos;
				if (revision !== this.number_revision || item_code !== (row.item_code || row.rm_item_code))
					return;
				ids.forEach((id, index) => frappe.utils.add_link_title("Serial No", id, numbers[index]));
				return super.parse_validate_and_set_in_model(ids.join("\n"), event);
			})();
			track_number_request(frm, pending);
			try {
				return await pending;
			} catch (error) {
				if (revision === this.number_revision) this.set_formatted_input(this.get_model_value());
				throw error;
			} finally {
				frm.serial_number_requests.delete(pending);
			}
		}

		serial_number_text(value) {
			const { row } = this.number_context();
			if (erpnext.serial_batch_input.is_pending(row, this.df.fieldname)) return value || "";
			return (value || "")
				.split("\n")
				.map((id) => frappe.utils.get_link_title("Serial No", id) || id)
				.join("\n");
		}

		async load_serial_titles(value) {
			if (erpnext.serial_batch_input.is_pending(this.number_context().row, this.df.fieldname)) return;
			const missing = (value || "")
				.split("\n")
				.filter((id) => id && !frappe.utils.get_link_title("Serial No", id));
			if (!missing.length) return;
			if (this.title_request_value !== value) {
				this.title_request_value = value;
				this.title_request = frappe.xcall(
					"erpnext.stock.serial_batch_identity.get_serial_batch_labels",
					{
						doctype: "Serial No",
						names: missing,
					}
				);
			}
			const labels = await this.title_request;
			Object.entries(labels).forEach(([id, label]) =>
				frappe.utils.add_link_title("Serial No", id, label)
			);
		}

		set_formatted_input(value) {
			if (!this.is_serial_list()) return super.set_formatted_input(value);
			super.set_formatted_input(this.serial_number_text(value));
			this.load_serial_titles(value).then(() => {
				if (this.get_model_value() === value && !this.$input?.is(":focus")) {
					super.set_formatted_input(this.serial_number_text(value));
				}
			});
		}

		set_disp_area(value) {
			if (!this.is_serial_list()) return super.set_disp_area(value);
			if (this.disp_area) $(this.disp_area).text(this.serial_number_text(value));
			this.load_serial_titles(value).then(() => {
				if (this.disp_area && this.get_model_value() === value) {
					$(this.disp_area).text(this.serial_number_text(value));
				}
			});
		}
	};

frappe.ui.form.ControlSmallText = with_serial_numbers(frappe.ui.form.ControlSmallText);
frappe.ui.form.ControlText = with_serial_numbers(frappe.ui.form.ControlText);
frappe.ui.form.ControlLongText = with_serial_numbers(frappe.ui.form.ControlLongText);

frappe.ui.form.ControlLink = class extends frappe.ui.form.ControlLink {
	async parse_validate_and_set_in_model(value, event, label) {
		const revision = (this.number_revision = (this.number_revision || 0) + 1);
		const doctype = this.get_options();
		const { frm, row } = this.serial_batch_context || { frm: this.frm, row: this.doc };
		const item_code = row?.item_code || row?.rm_item_code || row?.item;
		if (
			!frm ||
			!item_code ||
			!["Serial No", "Batch"].includes(doctype) ||
			(!event && label === undefined)
		) {
			return super.parse_validate_and_set_in_model(value, event, label);
		}

		if (
			doctype === "Batch" &&
			this.df.fieldname === "batch_no" &&
			row.parenttype &&
			frappe.meta.has_field(row.doctype, "serial_and_batch_bundle")
		) {
			await set_pending_number({ frm, row }, "batch_no", (label ?? this.get_label_value()).trim());
			return;
		}
		if (label !== undefined) erpnext.serial_batch_input.clear(row, this.df.fieldname);

		// Autocomplete supplies the selected physical label; change/blur supplies typed text.
		const number = (label ?? this.get_label_value()).trim();
		const pending = (async () => {
			let name = "";
			if (number) {
				const serial = doctype === "Serial No";
				const result = await frappe.xcall(
					"erpnext.stock.serial_batch_identity.resolve_serial_batch_numbers",
					{
						item_code,
						[serial ? "serial_numbers" : "batch_numbers"]: [number],
					}
				);
				name = result[serial ? "serial_nos" : "batch_nos"][0];
			}
			if (
				revision !== this.number_revision ||
				item_code !== (row?.item_code || row?.rm_item_code || row?.item)
			)
				return;
			return super.parse_validate_and_set_in_model(name, event, number);
		})();
		track_number_request(frm, pending);
		try {
			return await pending;
		} catch (error) {
			if (revision === this.number_revision) this.set_formatted_input(this.get_model_value());
			throw error;
		} finally {
			frm.serial_number_requests.delete(pending);
		}
	}
	set_formatted_input(value) {
		super.set_formatted_input(value);
		const { row } = this.serial_batch_context || { row: this.doc };
		if (this.df.fieldname === "batch_no" && erpnext.serial_batch_input.is_pending(row, "batch_no")) {
			this.$input?.val(value);
		}
	}
};

function split_physical_numbers(value) {
	return (value || "")
		.split(/[,\n]/)
		.map((number) => number.trim())
		.filter(Boolean);
}

async function set_pending_number({ frm, row }, field, value) {
	erpnext.serial_batch_input.mark(row, field, value);
	row[field] = value;
	frm.dirty();
	frm.refresh_field(row.parentfield || field);
	const values = {};
	if (frappe.meta.has_field(row.doctype, "use_serial_batch_fields")) values.use_serial_batch_fields = 1;
	if (frappe.meta.has_field(row.doctype, "serial_and_batch_bundle")) values.serial_and_batch_bundle = "";
	const pending = (async () => {
		await frappe.model.set_value(row.doctype, row.name, values);
		const numbers = split_physical_numbers(value);
		if (field === "serial_no" && numbers.length && !frm.doc.is_return && row.serial_no === value) {
			await frappe.model.set_value(
				row.doctype,
				row.name,
				"qty",
				numbers.length / (row.conversion_factor || 1)
			);
		}
	})();
	track_number_request(frm, pending);
	try {
		await pending;
	} finally {
		frm.serial_number_requests.delete(pending);
	}
}

function track_number_request(frm, pending) {
	if (!registered_forms.has(frm.doctype)) {
		registered_forms.add(frm.doctype);
		const wait = async (form) => {
			await Promise.all([...(form.serial_number_requests || [])]);
			for (const row of frappe.model.get_all_docs(form.doc)) {
				for (const field of [...(row.__serial_batch_input || [])]) {
					erpnext.serial_batch_input.is_pending(row, field);
				}
			}
		};
		frappe.ui.form.on(frm.doctype, {
			validate: wait,
			before_save: wait,
			after_save(form) {
				for (const row of frappe.model.get_all_docs(form.doc)) {
					delete row.__serial_batch_input;
					pending_values.delete(row);
				}
			},
		});
	}
	frm.serial_number_requests ||= new Set();
	frm.serial_number_requests.add(pending);
}

erpnext.serial_batch_input = {
	mark(row, field, value) {
		row.__serial_batch_input = [...new Set([...(row.__serial_batch_input || []), field])];
		const inputs = pending_values.get(row) || {};
		inputs[field] = value;
		pending_values.set(row, inputs);
	},
	is_pending(row, field) {
		if (!row?.__serial_batch_input?.includes(field)) return false;
		const inputs = pending_values.get(row);
		if (inputs && field in inputs && inputs[field] !== row[field]) {
			this.clear(row, field);
			return false;
		}
		return true;
	},
	clear(row, field) {
		if (!row?.__serial_batch_input) return;
		row.__serial_batch_input = row.__serial_batch_input.filter((name) => name !== field);
		if (!row.__serial_batch_input.length) delete row.__serial_batch_input;
		const inputs = pending_values.get(row);
		if (inputs) delete inputs[field];
	},
};
