frappe.treeview_settings["Healthcare Service Unit"] = {
	breadcrumbs: "Healthcare Service Unit",
	title: __("Healthcare Service Unit"),
	get_tree_root: false,
	filters: [{
		fieldname: "company",
		fieldtype: "Select",
		options: erpnext.utils.get_tree_options("company"),
		label: __("Company"),
		default: erpnext.utils.get_tree_default("company")
	}],
	get_tree_nodes: 'erpnext.healthcare.utils.get_children',
	ignore_fields:["parent_healthcare_service_unit"],
	onrender: function(node) {
		if (node.data.occupied_out_of_vacant!==undefined) {
			$('<span class="balance-area pull-right">'
				+ " " + node.data.occupied_out_of_vacant
				+ '</span>').insertBefore(node.$ul);
		}
		if (node.data && node.data.inpatient_occupancy!==undefined) {
			if (node.data.inpatient_occupancy == 1) {
				if (node.data.occupancy_status == "Occupied") {
					$('<span class="balance-area pull-right">'
						+ " " + node.data.occupancy_status
						+ '</span>').insertBefore(node.$ul);
				}
				if (node.data.occupancy_status == "Vacant") {
					$('<span class="balance-area pull-right">'
						+ " " + node.data.occupancy_status
						+ '</span>').insertBefore(node.$ul);
				}
			}
		}
	},
};
