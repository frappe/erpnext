// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Slab", {
	refresh(frm) {
		add_custom_badge(frm);
	},
});

function add_custom_badge(frm) {
    // Remove previous custom badge to avoid duplicates
    let label = '';
	let color = '';

    if (frm.doc.is_paused === 1) {
        label = __('Paused');
        color = 'yellow';
    }

    if (label) {
        const badge = $(`
            <span class="indicator-pill ${color} custom-extra-badge" style="margin-left:8px;">
                ${label}
            </span>
        `);

        frm.page.wrapper.find('.indicator-pill').last().after(badge);
    }
}
