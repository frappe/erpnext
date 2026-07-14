// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.ui.form.on("Pricing Scheme", {
	refresh(frm) {
		frm.trigger("setup_grids");
		frm.trigger("morph_tier_columns");
		frm.trigger("update_scope_summary");
		frm.trigger("render_dashboard");

		if (frm.is_new() && !(frm.doc.tiers || []).length) {
			frm.add_child("tiers", {});
			frm.refresh_field("tiers");
		}

		frm.add_custom_button(__("Test Pricing"), () => open_test_pricing_dialog(frm));
	},

	effect_type(frm) {
		frm.trigger("morph_tier_columns");
	},

	stacking_group(frm) {
		frm.trigger("refresh_overlaps");
	},

	priority(frm) {
		frm.trigger("refresh_overlaps");
	},

	valid_from(frm) {
		frm.trigger("refresh_overlaps");
	},

	valid_upto(frm) {
		frm.trigger("refresh_overlaps");
	},

	setup_grids(frm) {
		frm.fields_dict.trigger_scope.grid.set_multiple_add("value");
		frm.fields_dict.party_scope.grid.set_multiple_add("value");
	},

	morph_tier_columns(frm) {
		const is_free = frm.doc.effect_type === "Free Item";
		const is_margin = frm.doc.effect_type === "Margin";
		const grid = frm.fields_dict.tiers.grid;
		[
			"free_item",
			"free_qty",
			"free_item_uom",
			"free_item_rate",
			"recurrence_qty",
			"round_down_recurrence",
		].forEach((field) => grid.update_docfield_property(field, "hidden", is_free ? 0 : 1));
		grid.update_docfield_property("margin_type", "hidden", is_margin ? 0 : 1);
		grid.update_docfield_property("value", "hidden", is_free ? 1 : 0);
		grid.update_docfield_property(
			"value",
			"label",
			{
				Rate: __("Rate"),
				"Discount Percentage": __("Discount %"),
				"Discount Amount": __("Discount Amount"),
				Margin: __("Margin Value"),
				"Header Discount": __("Discount % on Total"),
			}[frm.doc.effect_type] || __("Value")
		);
		set_grid_label(
			frm,
			"tiers",
			{
				Rate: __("Fixed Rate Tiers"),
				"Discount Percentage": __("Percentage Discount Tiers"),
				"Discount Amount": __("Amount Discount Tiers"),
				Margin: __("Margin Tiers"),
				"Free Item": __("Free Item Tiers"),
				"Header Discount": __("Document Total Discount Tiers"),
			}[frm.doc.effect_type] || __("Tiers")
		);
		set_grid_help(
			frm,
			"tiers",
			{
				Rate: __("One row per quantity slab. Rate replaces the price list rate."),
				"Discount Percentage": __(
					"Enter the discount percent in the Discount % column — one row per quantity slab. Leave Min and Max Qty as 0 to always apply."
				),
				"Discount Amount": __(
					"Enter the per-unit discount amount — one row per quantity slab. Leave Min and Max Qty as 0 to always apply."
				),
				Margin: __("Margin added over the price list rate — one row per quantity slab."),
				"Free Item": __(
					"Free Qty per slab. Leave Free Item blank to give the purchased item itself. 'Per Every N Qty' repeats the freebie per dozen-style schemes."
				),
				"Header Discount": __("Discount percent applied on the document total."),
			}[frm.doc.effect_type] || ""
		);
		grid.refresh();
	},

	update_scope_summary(frm) {
		if (!(frm.doc.trigger_scope || []).some((row) => row.value || row.scope_type === "All Items")) {
			set_grid_description(
				frm,
				"trigger_scope",
				__("Scheme never applies if empty. Add at least one include row.")
			);
			return;
		}
		frappe.call({
			method: "erpnext.accounts.services.pricing.pricing_overlaps.count_scope_items",
			args: { scheme: frm.doc },
			callback: ({ message }) => {
				set_grid_description(
					frm,
					"trigger_scope",
					__("Matches approximately {0} items (subtree, excludes applied).", [message])
				);
			},
		});
	},

	render_dashboard(frm) {
		if (frm.is_new()) return;
		frm.trigger("render_usage");
		frm.trigger("refresh_overlaps");
	},

	render_usage(frm) {
		frappe.call({
			method: "erpnext.accounts.services.pricing.pricing_overlaps.get_usage",
			args: { scheme: frm.doc.name },
			callback: ({ message: usage }) => {
				frm.dashboard.add_indicator(
					__("Applications: {0}", [usage.applications]),
					usage.applications ? "green" : "gray"
				);
				frm.dashboard.add_indicator(
					__("Discount given: {0}", [format_currency(usage.discount_given)]),
					"blue"
				);
				if (usage.cap_total_applications) {
					const capped = usage.applications >= usage.cap_total_applications;
					frm.dashboard.add_indicator(
						__("Cap: {0} / {1}", [usage.applications, usage.cap_total_applications]),
						capped ? "red" : "orange"
					);
				}
			},
		});
	},

	refresh_overlaps: frappe.utils.debounce((frm) => {
		frappe.call({
			method: "erpnext.accounts.services.pricing.pricing_overlaps.detect_overlaps",
			args: { scheme: frm.doc },
			callback: ({ message: overlaps }) => render_overlaps(frm, overlaps || []),
		});
	}, 600),
});

frappe.ui.form.on("Pricing Scheme Item Scope", {
	value(frm) {
		frm.trigger("update_scope_summary");
		frm.trigger("refresh_overlaps");
	},
	exclude(frm) {
		frm.trigger("update_scope_summary");
	},
	trigger_scope_remove(frm) {
		frm.trigger("update_scope_summary");
		frm.trigger("refresh_overlaps");
	},
});

frappe.ui.form.on("Pricing Scheme Party Scope", {
	value(frm) {
		frm.trigger("refresh_overlaps");
	},
});

function set_grid_label(frm, fieldname, label) {
	// Grid labels, like descriptions, are only drawn once at creation.
	const grid = frm.fields_dict[fieldname].grid;
	grid.df.label = label;
	grid.wrapper.find(".control-label").first().text(label);
}

function set_grid_help(frm, fieldname, description) {
	// Keeps the grid description collapsed behind a help icon beside the
	// grid label; a click toggles it.
	const grid = frm.fields_dict[fieldname].grid;
	grid.df.description = description;
	const wrapper = $(grid.parent).find(".grid-description").html(description).hide();
	let icon = grid.wrapper.find(".grid-help-toggle");
	if (!icon.length) {
		icon = $(
			`<a class="grid-help-toggle text-muted" title="${__("Help")}">
				${frappe.utils.icon("circle-question-mark", "sm")}
			</a>`
		).insertAfter(grid.wrapper.find(".control-label").first());
		icon.on("click", () => wrapper.toggle());
	}
	icon.toggle(Boolean(description));
}

function set_grid_description(frm, fieldname, description) {
	// Grids render their description only once at creation (grid.js make()),
	// so frm.set_df_property never surfaces a description set later.
	const grid = frm.fields_dict[fieldname].grid;
	grid.df.description = description;
	$(grid.parent).find(".grid-description").html(description).toggle(Boolean(description));
}

function render_overlaps(frm, overlaps) {
	if (!frm.overlap_section) {
		frm.overlap_section = frm.dashboard.add_section("", __("Overlapping Schemes"));
	}
	const body = frm.overlap_section;
	body.empty();

	const conflict = overlaps.find((o) => o.severity === "conflict");
	if (conflict) {
		frm.set_intro(
			__("Conflicts with {0}: same stacking group and priority. Saving will be blocked.", [
				`<a href="/app/pricing-scheme/${conflict.scheme}">${frappe.utils.escape_html(
					conflict.title
				)}</a>`,
			]),
			"red"
		);
	} else {
		frm.set_intro("");
	}

	if (!overlaps.length) {
		body.append(`<div class="text-muted">${__("No overlapping schemes.")}</div>`);
		frm.dashboard.show();
		return;
	}

	const colors = { conflict: "red", shadowed: "orange", wins: "orange", stacks: "blue" };
	overlaps.forEach((o) => {
		body.append(`
			<div class="flex align-center" style="gap: 8px; padding: 3px 0;">
				<span class="indicator ${colors[o.severity]}"></span>
				<a href="/app/pricing-scheme/${o.scheme}">${frappe.utils.escape_html(o.title)}</a>
				<span class="text-muted small">${frappe.utils.escape_html(o.detail)}</span>
			</div>`);
	});
	frm.dashboard.show();
}

function open_test_pricing_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Test Pricing"),
		size: "large",
		fields: [
			{ fieldname: "customer", fieldtype: "Link", options: "Customer", label: __("Customer") },
			{
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				label: __("Company"),
				reqd: 1,
				default: frm.doc.company || frappe.defaults.get_user_default("Company"),
			},
			{ fieldname: "col1", fieldtype: "Column Break" },
			{
				fieldname: "transaction_date",
				fieldtype: "Date",
				label: __("Date"),
				default: frappe.datetime.get_today(),
			},
			{ fieldname: "coupon", fieldtype: "Link", options: "Coupon", label: __("Coupon") },
			{ fieldname: "sec1", fieldtype: "Section Break" },
			{
				fieldname: "items",
				fieldtype: "Table",
				label: __("Items"),
				cannot_add_rows: false,
				in_place_edit: true,
				fields: [
					{
						fieldname: "item_code",
						fieldtype: "Link",
						options: "Item",
						label: __("Item"),
						in_list_view: 1,
					},
					{ fieldname: "qty", fieldtype: "Float", label: __("Qty"), in_list_view: 1, default: 1 },
					{
						fieldname: "rate",
						fieldtype: "Currency",
						label: __("Rate (blank = price list)"),
						in_list_view: 1,
					},
				],
			},
			{ fieldname: "sec2", fieldtype: "Section Break" },
			{ fieldname: "results", fieldtype: "HTML" },
		],
		primary_action_label: __("Run"),
		primary_action(values) {
			frappe.call({
				method: "erpnext.accounts.services.pricing.pricing_preview.preview_pricing",
				args: {
					company: values.company,
					customer: values.customer,
					transaction_date: values.transaction_date,
					items: values.items || [],
					coupon: values.coupon,
				},
				callback: ({ message }) => render_preview(dialog, message),
			});
		},
	});
	dialog.show();
}

function render_preview(dialog, result) {
	const lines = (result.lines || [])
		.map(
			(l) => `<tr>
				<td>${frappe.utils.escape_html(l.item_code)}</td>
				<td class="text-right">${l.qty}</td>
				<td class="text-right">${format_currency(l.base_rate)}</td>
				<td class="text-right"><b>${format_currency(l.final_rate)}</b></td>
				<td class="small text-muted">${l.schemes.join(", ") || "—"}</td>
			</tr>`
		)
		.join("");
	const free = (result.free_items || [])
		.map(
			(f) =>
				`<tr><td>${frappe.utils.escape_html(f.item_code)}</td><td class="text-right">${
					f.qty
				}</td><td colspan="2" class="text-right">${__("Free")}</td><td class="small text-muted">${
					f.scheme
				}</td></tr>`
		)
		.join("");
	const trace = (result.trace || [])
		.map((t) => {
			const icon = t.status === "matched" ? "✓" : "✕";
			const cls = t.status === "matched" ? "text-success" : "text-muted";
			return `<div class="${cls} small">${icon} ${frappe.utils.escape_html(
				t.scheme
			)} — ${frappe.utils.escape_html(t.reason || t.status)}</div>`;
		})
		.join("");

	dialog.fields_dict.results.$wrapper.html(`
		<table class="table table-bordered table-sm">
			<thead><tr><th>${__("Item")}</th><th class="text-right">${__("Qty")}</th><th class="text-right">${__(
		"Base"
	)}</th><th class="text-right">${__("Final")}</th><th>${__("Schemes")}</th></tr></thead>
			<tbody>${lines}${free}</tbody>
		</table>
		<div style="margin-top: 8px;"><b class="small">${__("Trace")}</b>${
		trace || `<div class="text-muted small">${__("No candidate schemes.")}</div>`
	}</div>
	`);
}
