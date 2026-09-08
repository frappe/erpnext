// Resolve physical input before updating serial and batch links in the form model.
const registered_forms = new Set();
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

		async parse_validate_and_set_in_model(value, event) {
			const revision = (this.number_revision = (this.number_revision || 0) + 1);
			if (!this.is_serial_list() || !event) {
				return super.parse_validate_and_set_in_model(value, event);
			}
			const { frm, row } = this.number_context();
			const item_code = row.item_code || row.rm_item_code;
			const pending = (async () => {
				const numbers = (value || "")
					.split(/[,\n]/)
					.map((number) => number.trim())
					.filter(Boolean);
				const ids = numbers.length
					? await frappe.xcall(
							"erpnext.stock.serial_batch_identity.resolve_transaction_serial_numbers",
							{ parent: frm.doc, row, numbers }
					  )
					: [];
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
			return (value || "")
				.split("\n")
				.map((id) => frappe.utils.get_link_title("Serial No", id) || id)
				.join("\n");
		}

		async load_serial_titles(value) {
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
};

function track_number_request(frm, pending) {
	if (!registered_forms.has(frm.doctype)) {
		registered_forms.add(frm.doctype);
		const wait = (form) => Promise.all([...(form.serial_number_requests || [])]);
		frappe.ui.form.on(frm.doctype, { validate: wait, before_save: wait });
	}
	frm.serial_number_requests ||= new Set();
	frm.serial_number_requests.add(pending);
}
