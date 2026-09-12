import { split_numbers } from "./serial_batch_numbers";
import { format_serial_numbers, load_serial_titles, serial_number_text } from "./serial_batch_display";

const registered_forms = new Set();
const configured_fields = new WeakSet();
const configured_controls = new WeakSet();
const pending_values = new WeakMap();
const serial_list_fields = new Set(["serial_no", "rejected_serial_no", "current_serial_no"]);

$(document).on("form-refresh", (_event, frm) => {
	const doctypes = [frm.doctype, ...frappe.meta.get_table_fields(frm.doctype).map((df) => df.options)];
	for (const doctype of new Set(doctypes)) {
		for (const df of frappe.meta.get_docfields(doctype, frm.docname)) {
			setup_field(df);
		}
	}
	for (const control of frm.fields) setup_control(control);
});

$(document).on("grid-row-render", (_event, grid_row) => {
	for (const df of grid_row.docfields) {
		setup_field(df);
		if (is_serial_list(df) && grid_row.columns[df.fieldname]) grid_row.refresh_field(df.fieldname);
	}
});

function setup_field(df) {
	if (configured_fields.has(df) || !number_doctype(df)) return;
	configured_fields.add(df);
	const on_make = df.on_make;
	if (on_make !== setup_control) {
		df.on_make = on_make
			? (control) => {
					on_make(control);
					setup_control(control);
			  }
			: setup_control;
	}
	if (is_serial_list(df)) df.formatter = format_serial_numbers;
}

function setup_control(control) {
	const { df } = control;
	if (configured_controls.has(control) || !number_doctype(df)) return;
	const { frm } = get_context(control);
	if (!frm) return;
	setup_field(df);
	if (!control.$input) return;
	configured_controls.add(control);
	control.number_revision = 0;
	control.change = (event) => change_number(control, event);
	control.$input.on("input.serial-batch", () => {
		control.number_revision++;
		frm.dirty();
	});
	control.$input.on("awesomplete-selectcomplete.serial-batch", (event) => {
		control.number_revision++;
		if (event.originalEvent.text.value.includes("__link_option")) return;
		erpnext.serial_batch_input.clear(get_context(control).row, df.fieldname);
	});

	const set_formatted_input = control.set_formatted_input.bind(control);
	control.set_formatted_input = (value) => {
		const { row } = get_context(control);
		if (erpnext.serial_batch_input.is_pending(row, df.fieldname)) {
			control.$input.val(value || "");
		} else if (is_serial_list(df)) {
			const revision = control.number_revision;
			set_formatted_input(serial_number_text(value));
			load_serial_titles(value).then(() => {
				if (
					revision === control.number_revision &&
					row === get_context(control).row &&
					row[df.fieldname] === value &&
					!erpnext.serial_batch_input.is_pending(row, df.fieldname) &&
					!control.$input.is(":focus")
				) {
					set_formatted_input(serial_number_text(value));
				}
			});
		} else {
			set_formatted_input(value);
		}
	};
}

async function change_number(control, event) {
	if (event.type === "input") return;
	const { frm, row } = get_context(control);
	const value = control.$input.val().trim();
	if (!get_item_code(row)) {
		return control.parse_validate_and_set_in_model(control.get_input_value(), event);
	}
	const { df } = control;
	const serial_list = is_serial_list(df);
	const numbers = serial_list ? split_numbers(value) : value ? [value] : [];
	const revision = ++control.number_revision;
	if (
		row.parenttype &&
		frappe.meta.has_field(row.doctype, "serial_and_batch_bundle") &&
		(serial_list || df.fieldname === "batch_no")
	) {
		return set_pending_number({ frm, row }, df.fieldname, numbers.join("\n"));
	}
	return resolve_input(control, numbers, revision, (ids) =>
		control.parse_validate_and_set_in_model(serial_list ? ids.join("\n") : ids[0] || "", event)
	);
}

async function resolve_input(control, numbers, revision, apply) {
	const { frm, row } = get_context(control);
	const item_code = get_item_code(row);
	const previous_value = row[control.df.fieldname];
	const doctype = number_doctype(control.df);
	const is_current = () =>
		revision === control.number_revision &&
		row === get_context(control).row &&
		item_code === get_item_code(row) &&
		previous_value === row[control.df.fieldname];
	return run_number_request(frm, async () => {
		try {
			let ids = [];
			if (numbers.length) {
				const serial = doctype === "Serial No";
				const result = await frappe.xcall(
					"erpnext.stock.serial_batch_identity.resolve_serial_batch_numbers",
					{ item_code, [serial ? "serial_numbers" : "batch_numbers"]: numbers }
				);
				ids = result[serial ? "serial_nos" : "batch_nos"];
			}
			if (!is_current()) return;
			ids.forEach((id, index) => frappe.utils.add_link_title(doctype, id, numbers[index]));
			return await apply(ids);
		} catch (error) {
			if (is_current()) control.set_formatted_input(row[control.df.fieldname]);
			throw error;
		}
	});
}

function number_doctype(df) {
	if (
		!df.parent ||
		!["item_code", "rm_item_code", "item"].some((field) => frappe.meta.has_field(df.parent, field))
	)
		return;
	if (is_serial_list(df)) return "Serial No";
	if (df.fieldtype === "Link" && ["Serial No", "Batch"].includes(df.options)) return df.options;
}

function is_serial_list(df) {
	return (
		df.parent !== "Serial No" &&
		serial_list_fields.has(df.fieldname) &&
		["Small Text", "Text", "Long Text"].includes(df.fieldtype)
	);
}

function get_context(control) {
	return control.serial_batch_context || { frm: control.frm, row: control.doc };
}

function get_item_code(row) {
	return row?.item_code || row?.rm_item_code || row?.item;
}

async function set_pending_number({ frm, row }, field, value) {
	erpnext.serial_batch_input.mark(row, field, value);
	row[field] = value;
	frm.dirty();
	frm.refresh_field(row.parentfield || field);
	const values = {};
	if (frappe.meta.has_field(row.doctype, "use_serial_batch_fields")) values.use_serial_batch_fields = 1;
	if (frappe.meta.has_field(row.doctype, "serial_and_batch_bundle")) values.serial_and_batch_bundle = "";
	return run_number_request(frm, async () => {
		await frappe.model.set_value(row.doctype, row.name, values);
		const numbers = split_numbers(value);
		if (field === "serial_no" && numbers.length && !frm.doc.is_return && row.serial_no === value) {
			await frappe.model.set_value(
				row.doctype,
				row.name,
				"qty",
				numbers.length / (row.conversion_factor || 1)
			);
		}
	});
}

function run_number_request(frm, task) {
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
	const pending = Promise.resolve().then(task);
	frm.serial_number_requests.add(pending);
	return pending.finally(() => frm.serial_number_requests.delete(pending));
}

erpnext.serial_batch_input = {
	setup_control,
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
