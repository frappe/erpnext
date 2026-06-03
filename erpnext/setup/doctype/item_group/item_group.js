// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Item Group", {
	onload: function (frm) {
		frm.list_route = "Tree/Item Group";

		//get query select item group
		frm.fields_dict["parent_item_group"].get_query = function (doc, cdt, cdn) {
			return {
				filters: [
					["Item Group", "is_group", "=", 1],
					["Item Group", "name", "!=", doc.item_group_name],
				],
			};
		};
		frm.fields_dict["item_group_defaults"].grid.get_field("default_discount_account").get_query =
			function (doc, cdt, cdn) {
				const row = locals[cdt][cdn];
				return {
					filters: {
						report_type: "Profit and Loss",
						company: row.company,
						is_group: 0,
					},
				};
			};
		frm.fields_dict["item_group_defaults"].grid.get_field("expense_account").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: { company: row.company },
			};
		};
		frm.fields_dict["item_group_defaults"].grid.get_field("income_account").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_income_account",
				filters: { company: row.company },
			};
		};

		frm.fields_dict["item_group_defaults"].grid.get_field("buying_cost_center").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: row.company,
				},
			};
		};

		frm.fields_dict["item_group_defaults"].grid.get_field("selling_cost_center").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: row.company,
				},
			};
		};
	},

	refresh: function (frm) {
		frm.trigger("set_root_readonly");
		frm.add_custom_button(__("Item Group Tree"), function () {
			frappe.set_route("Tree", "Item Group");
		});

		if (!frm.is_new()) {
			frm.add_custom_button(__("Items"), function () {
				frappe.set_route("List", "Item", { item_group: frm.doc.name });
			});
		}
	},

	set_root_readonly: function (frm) {
		// read-only for root item group
		frm.set_intro("");
		if (!frm.doc.parent_item_group && !frm.doc.__islocal) {
			frm.set_read_only();
			frm.set_intro(__("This is a root item group and cannot be edited."), true);
		}
	},

	page_name: frappe.utils.warn_page_name_change,
});

frappe.ui.form.on("Item Default", {
	form_render: function (frm, cdt, cdn) {
		if (!frm.fields_dict["item_group_defaults"]) return;

		const row = locals[cdt][cdn];
		if (!row || !row.company) {
			Object.values(COMPANY_DEFAULTS_TO_VF).forEach((vf) => frappe.model.set_value(cdt, cdn, vf, ""));
			return;
		}

		setTimeout(() => {
			const $grid_row = frm.fields_dict["item_group_defaults"].grid.wrapper.find(
				`.grid-row[data-name="${cdn}"]`
			);
			$grid_row.find(".column-label").eq(1).text(__("Item Group Override"));
		}, 50);

		const $grid_row = frm.fields_dict["item_group_defaults"].grid.wrapper.find(
			`.grid-row[data-name="${cdn}"]`
		);

		if (!$grid_row.find(".item-defaults-desc").length) {
			$grid_row.find(".grid-form-body").prepend(`
				<div class="row">
					<div class="col-xs-12">
						<div class="item-defaults-desc" style="
							background: var(--control-bg);
							border-radius: var(--border-radius-sm);
							padding: 6px 6px 8px 14px;
							color: var(--text-muted);
						">
							${__(
								"Left column shows system-level defaults (Company / Stock Settings). Right column is where you set overrides for this item group."
							)}
						</div>
					</div>
				</div>
			`);
		}

		populate_item_group_company_defaults(frm, cdt, cdn, row);
	},

	company: function (frm, cdt, cdn) {
		if (!frm.fields_dict["item_group_defaults"]) return;

		const row = locals[cdt][cdn];
		if (!row || !row.company) {
			Object.values(COMPANY_DEFAULTS_TO_VF).forEach((vf) => frappe.model.set_value(cdt, cdn, vf, ""));
			return;
		}

		populate_item_group_company_defaults(frm, cdt, cdn, row);
	},
});

const COMPANY_DEFAULTS_TO_VF = {
	default_warehouse: "vf_default_warehouse",
	default_inventory_account: "vf_default_inventory_account",
	buying_cost_center: "vf_buying_cost_center",
	selling_cost_center: "vf_selling_cost_center",
	expense_account: "vf_expense_account",
	income_account: "vf_income_account",
	default_provisional_account: "vf_default_provisional_account",
	purchase_expense_account: "vf_purchase_expense_account",
	default_cogs_account: "vf_default_cogs_account",
	deferred_expense_account: "vf_deferred_expense_account",
	deferred_revenue_account: "vf_deferred_revenue_account",
	default_price_list: "vf_default_price_list",
	default_discount_account: "vf_default_discount_account",
	default_supplier: "vf_default_supplier",
	purchase_expense_contra_account: "vf_purchase_expense_contra_account",
};

const FIELD_DEFAULT_SOURCE = {
	default_warehouse: "Stock Settings",
	default_inventory_account: "Company",
	buying_cost_center: "Company",
	selling_cost_center: "Company",
	expense_account: "Company",
	income_account: "Company",
	default_provisional_account: "Company",
	purchase_expense_account: "Company",
	default_cogs_account: "Company",
	deferred_expense_account: "Company",
	deferred_revenue_account: "Company",
	default_price_list: null,
	default_discount_account: "Company",
	default_supplier: null,
	purchase_expense_contra_account: "Company",
};

function populate_item_group_company_defaults(frm, cdt, cdn, row) {
	const company = row.company;

	frappe.call({
		method: "erpnext.setup.doctype.item_group.item_group.get_company_resolved_defaults",
		args: { company: company },
		freeze: false,
		callback: function (r) {
			if (!r.message) return;

			const current_row = locals[cdt][cdn];
			if (!current_row || current_row.company !== company) return;

			const defaults = r.message;

			Object.entries(COMPANY_DEFAULTS_TO_VF).forEach(([key, vf_field]) => {
				frappe.model.set_value(cdt, cdn, vf_field, defaults[key] || "—");
			});

			setTimeout(() => update_item_group_vf_labels(frm, cdn, defaults), 50);
		},
	});
}

function update_item_group_vf_labels(frm, cdn, defaults) {
	const $grid_row = frm.fields_dict["item_group_defaults"].grid.wrapper.find(
		`.grid-row[data-name="${cdn}"]`
	);
	if (!$grid_row.length) return;

	Object.entries(COMPANY_DEFAULTS_TO_VF).forEach(([key, vf_field]) => {
		const $label = $grid_row.find(`[data-fieldname="${vf_field}"]`).find(".control-label, label").first();
		if (!$label.length) return;

		if (!$label.data("base-label")) {
			$label.data("base-label", $label.text().trim());
		}
		const base = $label.data("base-label");

		const source = FIELD_DEFAULT_SOURCE[key];
		$label.text(source ? `${base} (${__(source)})` : base);
	});
}
