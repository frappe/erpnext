frappe.provide("erpnext.edi");

erpnext.edi.import_genericode = function (listview_or_form) {
	let doctype = "Code List";
	let docname = undefined;
	if (listview_or_form.doc !== undefined) {
		docname = listview_or_form.doc.name;
	}
	new frappe.ui.FileUploader({
		method: "erpnext.edi.doctype.code_list.code_list_import.import_genericode",
		doctype: doctype,
		docname: docname,
		allow_web_link: false,
		allow_toggle_private: false,
		allow_take_photo: false,
		on_success: function (_file_doc, r) {
			listview_or_form.refresh();
			show_column_selection_dialog(r.message);
		},
	});
};

function show_column_selection_dialog(context) {
	let title_description = __("If there is no title column, use the code column for the title.");
	let default_title = get_default(context.columns, ["name", "Name", "code-name", "scheme-name"]);
	let fields = [
		{
			fieldtype: "HTML",
			fieldname: "code_list_info",
			options: `<div class="text-muted">${__(
				"You are importing data for the code list:"
			)} ${frappe.utils.get_form_link(
				"Code List",
				context.code_list,
				true,
				context.code_list_title
			)}</div>`,
		},
		{
			fieldtype: "Section Break",
		},
		{
			fieldname: "import_column",
			label: __("Import"),
			fieldtype: "Column Break",
		},
		{
			fieldname: "title_column",
			label: __("as Title"),
			fieldtype: "Select",
			reqd: 1,
			options: context.columns,
			default: default_title,
			description: default_title ? null : title_description,
		},
		{
			fieldname: "code_column",
			label: __("as Code"),
			fieldtype: "Select",
			options: context.columns,
			reqd: 1,
			default: get_default(context.columns, ["code", "Code", "value"]),
		},
		{
			fieldname: "filters_column",
			label: __("Filter"),
			fieldtype: "Column Break",
		},
	];

	if (context.columns.length > 2) {
		fields.splice(5, 0, {
			fieldname: "description_column",
			label: __("as Description"),
			fieldtype: "Select",
			options: [null].concat(context.columns),
			default: get_default(context.columns, [
				"description",
				"Description",
				"remark",
				__("description"),
				__("Description"),
			]),
		});
	}

	// Add filterable columns
	for (let column in context.filterable_columns) {
		fields.push({
			fieldname: `filter_${column}`,
			label: __("by {}", [frappe.utils.escape_html(column)]),
			fieldtype: "Select",
			options: [null].concat(
				context.filterable_columns[column].map((value) => ({
					label: frappe.utils.escape_html(value),
					value: value,
				}))
			),
		});
	}

	fields.push(
		{
			fieldname: "preview_section",
			label: __("Preview"),
			fieldtype: "Section Break",
		},
		{
			fieldname: "preview_html",
			fieldtype: "HTML",
		}
	);

	let d = new frappe.ui.Dialog({
		title: __("Select Columns and Filters"),
		fields: fields,
		primary_action_label: __("Import"),
		size: "large", // This will make the modal wider
		primary_action(values) {
			let filters = {};
			for (let field in values) {
				if (field.startsWith("filter_") && values[field]) {
					filters[field.replace("filter_", "")] = values[field];
				}
			}
			frappe
				.xcall("erpnext.edi.doctype.code_list.code_list_import.process_genericode_import", {
					code_list_name: context.code_list,
					file_name: context.file,
					code_column: values.code_column,
					title_column: values.title_column,
					description_column: values.description_column,
					filters: filters,
				})
				.then((count) => {
					frappe.msgprint(__("Import completed. {0} common codes created.", [count]));
				});
			d.hide();
		},
	});

	d.fields_dict.code_column.df.onchange = () => update_preview(d, context);
	d.fields_dict.title_column.df.onchange = (e) => {
		let field = d.fields_dict.title_column;
		if (!e.target.value) {
			field.df.description = title_description;
			field.refresh();
		} else {
			field.df.description = null;
			field.refresh();
		}
		update_preview(d, context);
	};

	// Add onchange events for filterable columns
	for (let column in context.filterable_columns) {
		d.fields_dict[`filter_${column}`].df.onchange = () => update_preview(d, context);
	}

	d.show();
	update_preview(d, context);
}

/**
 * Return the first key from the keys array that is found in the columns array.
 */
function get_default(columns, keys) {
	return keys.find((key) => columns.includes(key));
}

function update_preview(dialog, context) {
	let code_column = dialog.get_value("code_column");
	let title_column = dialog.get_value("title_column");
	let description_column = dialog.get_value("description_column");

	let html = '<table class="table table-bordered"><thead><tr>';
	if (title_column) html += `<th>${__("Title")}</th>`;
	if (code_column) html += `<th>${__("Code")}</th>`;
	if (description_column) html += `<th>${__("Description")}</th>`;

	// Add headers for filterable columns
	for (let column in context.filterable_columns) {
		if (dialog.get_value(`filter_${column}`)) {
			html += `<th>${frappe.utils.escape_html(column)}</th>`;
		}
	}

	html += "</tr></thead><tbody>";

	for (let i = 0; i < 3; i++) {
		html += "<tr>";
		if (title_column) {
			html += preview_cell(context.example_values[title_column][i]);
		}
		if (code_column) {
			html += preview_cell(context.example_values[code_column][i]);
		}
		if (description_column) {
			html += preview_cell(context.example_values[description_column][i]);
		}

		// Add values for filterable columns
		for (let column in context.filterable_columns) {
			if (dialog.get_value(`filter_${column}`)) {
				html += preview_cell(context.example_values[column][i]);
			}
		}

		html += "</tr>";
	}

	html += "</tbody></table>";

	dialog.fields_dict.preview_html.$wrapper.html(html);
}

function truncate(value, maxLength = 40) {
	if (typeof value !== "string") return "";
	return value.length > maxLength ? value.substring(0, maxLength - 3) + "..." : value;
}

function preview_cell(value) {
	value = value || "";
	return `<td title="${frappe.utils.escape_html(value)}">${frappe.utils.escape_html(truncate(value))}</td>`;
}
