// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Engineering Design", {
	setup(frm) {
		frm.set_query("item_code", "parts", () => ({ filters: { disabled: 0 } }));
		frm.set_query("item_code", () => ({ filters: { disabled: 0 } }));
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("Company"));
		}
	},

	refresh(frm) {
		frm.page.sidebar.toggle(false);
		frm.page.wrapper.css("--page-max-width", "100%");
		frm.events.render_design_view(frm);
		frm.events.add_actions(frm);
	},

	track_semi_finished_goods(frm) {
		frm.design_view?.render();
	},

	design_file(frm) {
		if (frm.doc.design_file && frm.doc.company) {
			frm.save();
		}
	},

	async render_design_view(frm) {
		await frappe.require("engineering_design.bundle.js");
		frm.design_view ??= new erpnext.manufacturing.EngineeringDesignView(frm);
		frm.design_view.refresh();
	},

	add_actions(frm) {
		frm.compare_button?.remove();
		frm.compare_button = null;
		if (frm.doc.previous_revision && frm.doc.docstatus < 2) {
			frm.compare_button = frm.page.add_action_icon(
				"git-compare",
				() => frm.events.show_revision_changes(frm),
				"",
				__("Compare with Previous Revision")
			);
		}

		if (frm.doc.docstatus !== 1 || frm.doc.status === "Superseded") return;

		if (frm.doc.status === "Approved") {
			frm.add_custom_button(__("Suggest Items"), () => frm.events.suggest_items(frm), __("Map Items"));
			frm.add_custom_button(
				__("Create Missing Items"),
				() => frm.events.create_items(frm),
				__("Map Items")
			);
			frm.add_custom_button(__("Create BOMs"), () => frm.events.create_boms(frm)).addClass(
				"btn-primary"
			);
		}

		frm.add_custom_button(__("New Revision"), () =>
			frm
				.call("make_new_revision")
				.then((r) => frappe.set_route("Form", "Engineering Design", r.message))
		);
	},

	async suggest_items(frm) {
		const { message: suggestions } = await frm.call("get_suggested_items");
		const rows = frm.doc.parts.filter((row) => suggestions[row.name]);
		if (!rows.length) {
			frappe.show_alert({ message: __("No matching items found"), indicator: "orange" });
			return;
		}

		for (const row of rows) {
			await frappe.model.set_value(row.doctype, row.name, "item_code", suggestions[row.name]);
		}
		await frm.save("Update");
		frappe.show_alert({ message: __("{0} parts mapped", [rows.length]), indicator: "green" });
	},

	create_items(frm) {
		frappe.prompt(
			[
				{
					fieldname: "item_group",
					fieldtype: "Link",
					options: "Item Group",
					label: __("Item Group"),
					reqd: 1,
					get_query: () => ({ filters: { is_group: 0 } }),
				},
				{
					fieldname: "stock_uom",
					fieldtype: "Link",
					options: "UOM",
					label: __("Default Unit of Measure"),
					reqd: 1,
					default: "Nos",
				},
			],
			async (values) => {
				const { message: created } = await frm.call("create_items", values);
				await frm.reload_doc();
				frappe.show_alert({ message: __("{0} items created", [created.length]), indicator: "green" });
				await frm.design_view?.make_item_images(created);
			},
			__("Create Items for Parts Without an Item"),
			__("Create")
		);
	},

	create_boms(frm) {
		if (frm.is_dirty()) {
			frappe.msgprint(__("Save the design before creating BOMs."));
			return;
		}

		frm.call({ method: "create_boms", doc: frm.doc, freeze: true }).then((r) => {
			frm.reload_doc();
			const links = r.message.map((bom) => frappe.utils.get_form_link("BOM", bom, true));
			frappe.msgprint(__("Created BOMs: {0}", [links.join(", ")]));
		});
	},

	async show_revision_changes(frm) {
		const { message: changes } = await frm.call("get_revision_changes");
		const sections = [
			[__("Added"), changes.added],
			[__("Removed"), changes.removed],
			[__("Quantity Changed"), changes.quantity_changed],
		].filter(([, rows]) => rows.length);

		if (!sections.length) {
			frappe.msgprint(__("This revision has the same parts as {0}.", [frm.doc.previous_revision]));
			return;
		}

		const dialog = new frappe.ui.Dialog({
			title: __("Changes from {0}", [frm.doc.previous_revision]),
			size: "large",
		});
		dialog.$body.html(sections.map(([title, rows]) => get_changes_table(title, rows)).join(""));
		dialog.show();
	},
});

function get_changes_table(title, rows) {
	const cell = (value, align = "left") =>
		`<td class="ellipsis" style="text-align:${align};max-width:280px;" title="${frappe.utils.escape_html(
			value
		)}">
			${frappe.utils.escape_html(value)}</td>`;
	const quantity = (value) =>
		value === null ? "" : format_number(value, null, Number.isInteger(value) ? 0 : 3);

	return `<h5 style="margin-top:var(--margin-md);">${title}</h5>
		<table class="table table-bordered" style="table-layout:fixed;">
			<thead><tr>
				<th>${__("Part")}</th>
				<th>${__("Path")}</th>
				<th style="text-align:right;width:170px;">${__("Previous Quantity")}</th>
				<th style="text-align:right;width:100px;">${__("Quantity")}</th>
			</tr></thead>
			<tbody>${rows
				.map(
					(row) =>
						`<tr>${cell(row.part_name || row.part_number)}${cell(row.path)}${cell(
							quantity(row.previous_quantity),
							"right"
						)}${cell(quantity(row.quantity), "right")}</tr>`
				)
				.join("")}</tbody>
		</table>`;
}
