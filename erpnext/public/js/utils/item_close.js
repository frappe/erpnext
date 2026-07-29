erpnext.item_close = {
	add_buttons(frm, config) {
		if (frm.doc.docstatus != 1 || !frm.has_perm("submit")) {
			return;
		}

		if (frm.doc.status != "Closed" && frm.doc.items.some((item) => config.is_closable(item))) {
			frm.add_custom_button(
				__("Close Items"),
				() => erpnext.item_close.select_rows(frm, config, 1),
				__("Status")
			);
		}

		if (frm.doc.items.some((item) => item.closed)) {
			frm.add_custom_button(
				__("Reopen Items"),
				() => erpnext.item_close.select_rows(frm, config, 0),
				__("Status")
			);
		}
	},

	select_rows(frm, config, closed) {
		const rows = frm.doc.items
			.filter((item) => (closed ? config.is_closable(item) : item.closed))
			.map((item) => Object.assign({ name: item.name }, config.summarise(item)));

		const dialog = new frappe.ui.Dialog({
			title: closed ? __("Close Items") : __("Reopen Items"),
			size: "large",
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "help",
					options: closed ? `<p class="text-muted small">${config.help}</p>` : "",
				},
				{
					fieldname: "items",
					fieldtype: "Table",
					data: rows,
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: false,
					fields: [
						{ fieldname: "name", fieldtype: "Data", read_only: 1, hidden: 1 },
					].concat(config.columns),
				},
			],
			primary_action_label: closed ? __("Close") : __("Reopen"),
			primary_action: () => {
				const selected = dialog.fields_dict.items.grid
					.get_selected_children()
					.map((row) => row.name);

				if (!selected.length) {
					frappe.msgprint(__("Select at least one row"));
					return;
				}

				dialog.hide();
				frappe.call({
					method: "erpnext.controllers.item_close.update_closed_status",
					args: {
						doctype: frm.doc.doctype,
						name: frm.doc.name,
						item_names: selected,
						closed: closed,
					},
					freeze: true,
					callback: () => frm.reload_doc(),
				});
			},
		});

		dialog.show();
	},

	column(fieldname, label, fieldtype = "Float", columns = 1) {
		return {
			fieldname: fieldname,
			fieldtype: fieldtype,
			label: label,
			in_list_view: 1,
			read_only: 1,
			columns: columns,
		};
	},
};
