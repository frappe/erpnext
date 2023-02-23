frappe.listview_settings['Auto Reconcile Log'] = {
	add_fields: ["allocated", "reconciled", "reconciled_entries", "total_allocations", "error_log"],
	get_indicator: function(doc) {
		if (doc.reconciled) {
			return [__("Reconciled"), "green", "reconciled,=,True"];
		} else if (doc.allocated) {
			if (doc.error_log) {
				if (doc.total_allocations && doc.reconciled_entries > 0 && doc.reconciled_entries != doc.total_allocations) {
					return [__("Partially Reconciled"), "orange", "allocated,=,True"];
				} else if (doc.total_allocations && doc.reconciled_entries == 0) {
					return [__("Failed"), "red", "allocated,=,True"];
				}
			} else {
				if (doc.total_allocations && doc.reconciled_entries > 0 && doc.reconciled_entries != doc.total_allocations) {
					return [__("Running"), "blue", "allocated,=,True"];
				}
			}
		} else {
			return [__("Queued"), "orange", ""];
		}
	},
};
