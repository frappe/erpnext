// set from the opportunity's quotations on every save
const OPPORTUNITY_SYSTEM_STATUSES = ["Quotation", "Converted"];

frappe.kanban_v2.settings["Opportunity"] = {
	callbacks: {
		canMoveCard(card, from, to) {
			// only on boards grouped by status
			if (card.status !== from) return;
			const status = [to, from].find((s) => OPPORTUNITY_SYSTEM_STATUSES.includes(s));
			if (!status) return;
			frappe.ui.toast({
				id: "opportunity-kanban-system-status",
				message: __("{0} is set from the opportunity's quotations", [__(status)]),
				type: "warning",
			});
			return false;
		},

		onBeforeCardMove(move) {
			if (move.toColumn !== "Lost") return;
			if (move.cardIds.length > 1) {
				frappe.ui.toast({
					id: "opportunity-kanban-lost",
					message: __("Declare opportunities lost one at a time"),
					type: "warning",
				});
				return false;
			}
			return declare_opportunity_lost(move.cardId);
		},
	},
};

// the form's Set as Lost dialog; resolves true once the opportunity is lost
function declare_opportunity_lost(name) {
	return new Promise((resolve) => {
		let declared = false;
		const dialog = new frappe.ui.Dialog({
			title: __("Set as Lost"),
			fields: erpnext.pre_sales.lost_reason_fields("Opportunity"),
			primary_action_label: __("Declare Lost"),
			primary_action(values) {
				frappe
					.call({
						method: "run_doc_method",
						args: {
							dt: "Opportunity",
							dn: name,
							method: "declare_enquiry_lost",
							args: {
								lost_reasons_list: values.lost_reason,
								competitors: values.competitors || [],
								detailed_reason: values.detailed_reason,
							},
						},
					})
					.then(() => {
						declared = true;
						dialog.hide();
					});
			},
		});
		dialog.onhide = () => resolve(declared);
		dialog.show();
	});
}
