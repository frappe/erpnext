// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.pricing_scheme");

const PRICING_PANEL_DOCTYPES = [
	"Quotation",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
];

erpnext.pricing_scheme.render_panel = function (frm) {
	frm.toggle_display("pricing_scheme_section", false);
	if (frm.is_new()) return;
	frappe.call({
		method: "erpnext.accounts.services.pricing.pricing_preview.explain_pricing",
		args: { doctype: frm.doc.doctype, name: frm.doc.name },
		callback: ({ message }) => {
			if (message && message.enabled) {
				render_pricing_panel(frm, message);
			}
		},
	});
};

function render_pricing_panel(frm, data) {
	frm.toggle_display("pricing_scheme_section", true);
	const body = frm.get_field("pricing_scheme_explanation").$wrapper;
	body.empty();

	(data.applied || []).forEach((entry) => body.append(applied_row(frm, entry)));
	if (!(data.applied || []).length) {
		body.append(`<div class="text-muted">${__("No pricing schemes apply.")}</div>`);
	}
	if (data.coupon) {
		body.append(coupon_row(data.coupon));
	}
	if (data.inherited_lines) {
		body.append(
			`<div class="text-muted small" style="padding: 3px 0;">${__(
				"{0} lines keep the pricing agreed on their source document.",
				[data.inherited_lines]
			)}</div>`
		);
	}
	(data.trace || [])
		.filter((entry) => entry.status !== "matched")
		.forEach((entry) =>
			body.append(`
				<div class="small text-muted" style="padding: 2px 0;">
					✕ <a href="/app/pricing-scheme/${entry.scheme}">${frappe.utils.escape_html(entry.title)}</a>
					${frappe.utils.escape_html(entry.reason || entry.status)}
				</div>`)
		);
}

function applied_row(frm, entry) {
	const parts = [];
	if (entry.discount_amount) {
		parts.push(__("saves {0}", [format_currency(entry.discount_amount, frm.doc.currency)]));
	}
	(entry.free_items || []).forEach((free) =>
		parts.push(__("adds {0} × {1} free", [free.qty, frappe.utils.escape_html(free.item_code)]))
	);
	return `
		<div class="flex align-center" style="gap: 8px; padding: 3px 0;">
			<span class="indicator green"></span>
			<a href="/app/pricing-scheme/${entry.scheme}">${frappe.utils.escape_html(entry.title)}</a>
			<span class="text-muted small">${parts.join(" · ")}</span>
		</div>`;
}

function coupon_row(coupon) {
	const state = coupon.ok ? `<span class="indicator green"></span>` : `<span class="indicator red"></span>`;
	const detail = coupon.ok
		? __("unlocks {0}", [frappe.utils.escape_html(coupon.title || coupon.scheme)])
		: frappe.utils.escape_html(coupon.reason || __("not applicable"));
	return `
		<div class="flex align-center" style="gap: 8px; padding: 3px 0;">
			${state}
			<span>${__("Coupon {0}", [frappe.utils.escape_html(coupon.code)])}</span>
			<span class="text-muted small">${detail}</span>
		</div>`;
}

PRICING_PANEL_DOCTYPES.forEach((doctype) =>
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			erpnext.pricing_scheme.render_panel(frm);
		},
	})
);
