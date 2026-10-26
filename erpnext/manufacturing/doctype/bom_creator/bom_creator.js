// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("BOM Creator", {
	setup(frm) {
		frm.set_query("item_code", "items", () => ({ filters: { disabled: 0 } }));
		frm.set_query("item_code", (doc) => ({
			query: "erpnext.controllers.queries.item_query",
			filters: { is_stock_item: doc.is_phantom ? 0 : 1 },
		}));
		frm.set_query("bom_no", "items", (doc, cdt, cdn) => ({
			filters: { item: locals[cdt][cdn].item_code, docstatus: 1 },
		}));
		frm.set_query("default_warehouse", (doc) => ({ filters: { company: doc.company, is_group: 0 } }));
		frm.get_field("design_file").df.options = {
			restrictions: { allowed_file_types: [".step", ".stp", ".csv"] },
		};
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
		frm.previous_item_name = frm.doc.item_name;
		if (frm.doc.status === "Failed") {
			frm.dashboard.set_headline(
				__("The BOMs could not be created. See the Error Log in the Details tab."),
				"red"
			);
		}
	},

	company(frm) {
		if (frm.doc.company) {
			frm.set_value("currency", erpnext.get_currency(frm.doc.company));
		}
	},

	track_semi_finished_goods(frm) {
		frm.design_view?.render();
	},

	qty(frm) {
		frm.design_view?.render();
	},

	item_code(frm) {
		frm.design_view?.render();
		if (frm.is_new()) frm.events.read_design_file(frm);
	},

	item_name(frm) {
		const follows_item = !frm.doc.design_name || frm.doc.design_name === frm.previous_item_name;
		if (follows_item && frm.doc.item_name) {
			frm.set_value("design_name", frm.doc.item_name);
		}
		frm.previous_item_name = frm.doc.item_name;
		frm.design_view?.render();
	},

	design_name(frm) {
		frm.design_view?.render();
	},

	design_file(frm) {
		frm.events.read_design_file(frm);
	},

	read_design_file(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.design_file && frm.doc.company && frm.doc.item_code) {
			frm.save();
		}
	},

	async render_design_view(frm) {
		await frappe.require("bom_creator.bundle.js");
		frm.design_view ??= new erpnext.manufacturing.BOMCreatorView(frm);
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

		if (["Submitted", "Failed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Suggest Items"), () => frm.events.suggest_items(frm), __("Map Items"));
			frm.add_custom_button(
				__("Create Missing Items"),
				() => frm.events.create_items(frm),
				__("Map Items")
			);
		}

		if (["Submitted", "Failed", "In Progress"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Create BOMs"), () => frm.events.create_boms(frm)).addClass(
				"btn-primary"
			);
		}

		frm.add_custom_button(__("New Revision"), () =>
			frm.call("make_new_revision").then((r) => frappe.set_route("Form", "BOM Creator", r.message))
		);
	},

	async suggest_items(frm) {
		const { message: matches } = await frm.call({
			method: "get_suggested_items",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Matching parts to items..."),
		});
		const groups = frm.events.get_unmapped_part_groups(frm);
		if (!groups.length) {
			frappe.show_alert({ message: __("All parts are mapped to items"), indicator: "green" });
			return;
		}

		const dialog = new frappe.ui.Dialog({
			title: __("Map Items"),
			size: "extra-large",
			fields: [
				{
					fieldname: "parts",
					fieldtype: "Table",
					label: __("Parts Without an Item"),
					cannot_add_rows: 1,
					cannot_delete_rows: 1,
					in_place_edit: 1,
					data: groups.map((rows) => frm.events.get_mapping_row(rows, matches[rows[0].name])),
					fields: [
						{
							fieldname: "part_number",
							fieldtype: "Data",
							label: __("Part Number"),
							read_only: 1,
							in_list_view: 1,
							columns: 2,
						},
						{
							fieldname: "part_name",
							fieldtype: "Data",
							label: __("Part Name"),
							read_only: 1,
							in_list_view: 1,
							columns: 3,
						},
						{
							fieldname: "item_code",
							fieldtype: "Link",
							options: "Item",
							label: __("Item"),
							in_list_view: 1,
							columns: 3,
							get_query: () => ({ filters: { disabled: 0, has_variants: 0 } }),
							onchange() {
								frm.events.update_mapping_row(this.grid_row, this.get_value());
							},
						},
						{
							fieldname: "matched_on",
							fieldtype: "Data",
							label: __("Matched On"),
							placeholder: " ",
							read_only: 1,
							in_list_view: 1,
							columns: 1,
						},
						{
							fieldname: "score",
							fieldtype: "Data",
							label: __("Score"),
							placeholder: " ",
							read_only: 1,
							in_list_view: 1,
							columns: 1,
						},
					],
				},
			],
			primary_action_label: __("Map"),
			primary_action: async () => {
				const rows = dialog.fields_dict.parts.grid
					.get_selected_children()
					.filter((row) => row.item_code);
				if (!rows.length) {
					frappe.msgprint(__("Select the parts to map and set their items."));
					return;
				}

				dialog.hide();
				await frm.events.map_parts(frm, rows);
			},
		});
		dialog.$wrapper.addClass("bom-creator-map-items").append(`<style>
			.bom-creator-map-items .grid-row > .row .col.grid-data-last { justify-content: flex-end; align-items: flex-start; text-align: right; }
		</style>`);
		dialog.show();
	},

	get_unmapped_part_groups(frm) {
		const groups = {};
		for (const row of frm.doc.items || []) {
			const key = row.part_number || row.part_name;
			if (!row.item_code && !row.exclude_from_bom && key) (groups[key] ||= []).push(row);
		}
		return Object.values(groups);
	},

	get_mapping_row(rows, match = {}) {
		const suggestion = {
			item_code: match.item_code,
			score: match.score ? `${match.score}%` : "",
			matched_on: match.matched_on ? __(match.matched_on) : "",
		};
		return {
			...suggestion,
			suggestion,
			part_number: rows[0].part_number,
			part_name: rows[0].part_name,
			part_names: rows.map((row) => row.name),
			__checked: match.is_selected ? 1 : 0,
		};
	},

	update_mapping_row(grid_row, item_code) {
		const { suggestion } = grid_row.doc;
		const is_suggested = item_code === suggestion.item_code;
		Object.assign(grid_row.doc, {
			score: is_suggested ? suggestion.score : "",
			matched_on: is_suggested ? suggestion.matched_on : item_code ? __("Manual") : "",
		});
		grid_row.select(!!item_code);
		grid_row.refresh_check();
		for (const fieldname of ["score", "matched_on"]) {
			grid_row.refresh_field(fieldname, grid_row.doc[fieldname]);
		}
	},

	async map_parts(frm, rows) {
		for (const row of rows) {
			for (const name of row.part_names) {
				await frappe.model.set_value("BOM Creator Item", name, "item_code", row.item_code);
			}
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
					default: frm.doc.item_group,
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

		frm.call({ method: "enqueue_create_boms", doc: frm.doc, freeze: true }).then(() => frm.reload_doc());
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
