frappe.treeview_settings["Location"] = {
	ignore_fields: ["parent_location"],
	get_tree_nodes: 'erpnext.assets.doctype.location.location.get_children',
	add_tree_node: 'erpnext.assets.doctype.location.location.add_node',
	filters: [
		{
			fieldname: "location",
			fieldtype: "Link",
			options: "Location",
			label: __("Location"),
			get_query: function () {
				return {
					filters: [["Location", "is_group", "=", 1]]
				};
			}
		},
	],
	breadcrumb: "Assets",
	root_label: "All Locations",
	get_tree_root: false,
	menu_items: [
		{
			label: __("New Location"),
			action: function () {
				frappe.new_doc("Location", true);
			},
			condition: 'frappe.boot.user.can_create.indexOf("Location") !== -1'
		}
	],
	onrender: function (node) {

		if (!node.is_root) {
			frappe.db.get_value("Location", node.data.value, "area")
				.then((r) => {
					// Place the location area on the right side, tree accounts style.
					$('<span class="balance-area pull-right text-muted small">'
						+ (`${((flt(r.message.area)).toLocaleString('en') + ' Sq m')}`)
						+ '</span>').insertBefore(node.$ul);
				});
		}

		// Applies when filter is applied in tree view
		if (!node.parent_label) {
			frappe.db.get_value("Location", node.data.value, "area")
				.then((r) => {
					if (r.message) {
						$('<span class="balance-area pull-right text-muted small">'
							+ (`${((flt(r.message.area)).toLocaleString('en') + ' Sq m')}`)
							+ '</span>').insertBefore(node.$ul);
					}
				});
		}

		if (node.data.value == 'All Locations') {
			// Get the total of all locations in square meters
			frappe.call({
				method: "erpnext.assets.doctype.location.location.get_total_location",
				callback: function (r) {
					// console.log(r.message);
					$('<span class="balance-area pull-right text-muted small">'
						+ (`${((flt(r.message)).toLocaleString('en') + ' Sq m')}`)
						+ '</span>').insertBefore(node.$ul);
				}
			});
		}

	},
	onload: function (treeview) {
		treeview.make_tree();
	}
};