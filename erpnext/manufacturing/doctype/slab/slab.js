// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
const UN_MOVABLE_STAGES = ["Re-Pressing", "Polishing", "Packed", "Shipped", "Discarded", "Quality Check"];

frappe.ui.form.on("Slab", {
	refresh(frm) {
		add_custom_badge(frm);

		if (!frm.doc.__islocal && !UN_MOVABLE_STAGES.includes(frm.doc.status)) {
			frm.add_custom_button(__('Move To'), () => {
				let current_stage = frm.doc.status;

				frappe.call({
					method: "erpnext.manufacturing.doctype.slab.api.get_valid_next_stages",
					args: { current_stage: current_stage },
					callback: function(r) {
						if (r.message && r.message.length > 0) {
							let dialog = new frappe.ui.Dialog({
								title: __('Move Slab'),
								fields: [
									{
										label: __('Move To Stage and Finish'),
										fieldname: 'next_stage',
										fieldtype: 'Select',
										options: r.message,
										reqd: 1
									}
								],
								primary_action_label: __('Move'),
								primary_action: function(values) {
									let $btn = dialog.get_primary_btn();
									$btn.prop('disabled', true);
									let $loading_bar = $(`<div class="my-3 loading-progress-container">
										<p class="text-muted small mb-2">${__("Moving slab to {0}...", [values.next_stage])}</p>
										<div class="progress">
											<div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 100%"></div>
										</div>
									</div>`);
									dialog.$wrapper.find('.modal-body').append($loading_bar);

									frappe.call({
										method: "erpnext.manufacturing.doctype.slab.api.move_slab_iteratively_to",
										args: {
											slab_name: frm.doc.name,
											final_stage: values.next_stage,
										},
										callback: function() {
											frappe.msgprint(__('Slab moved successfully'));
											frm.reload_doc();
											dialog.hide();
										},
										always: function() {
											$btn.prop('disabled', false);
											$loading_bar.remove();
										}
									});
								}
							});
							dialog.show();
						} else {
							frappe.msgprint({
								title: __('Validation Error'),
								indicator: 'orange',
								message: __('No valid next stages available for the current stage: {0}.', [current_stage])
							});
						}
					}
				});
			});
		}
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
