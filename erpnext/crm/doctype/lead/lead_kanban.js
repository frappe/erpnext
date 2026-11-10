// set from the lead's opportunities, quotations and customer on every save
const LEAD_SYSTEM_STATUSES = ["Opportunity", "Quotation", "Lost Quotation", "Converted"];

frappe.kanban_v2.settings["Lead"] = {
	callbacks: {
		canMoveCard(card, from, to) {
			// only on boards grouped by status
			if (card.status !== from) return;
			const status = [to, from].find((s) => LEAD_SYSTEM_STATUSES.includes(s));
			if (!status) return;
			frappe.ui.toast({
				id: "lead-kanban-system-status",
				message: __("{0} is set from the lead's linked documents", [__(status)]),
				type: "warning",
			});
			return false;
		},
	},
};
