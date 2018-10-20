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
		let page = $(document);

		if (!node.is_root) {
			frappe.db.get_value("Location", node.data.value, "area")
				.then((r) => {

					if (r.message.area) {
						let x = page.find(`span[data-label="${node.data.value}"] .tree-label`);
						x.text(`${x.text()} ( ${((flt(r.message.area)).toLocaleString('en') + ' Square Meters ')})`);
					}

				});
		} else {
			//Get the total of all locations in square meters
			frappe.call({
				method: "erpnext.assets.doctype.location.utils_location.get_total_location",
				callback: function (r) {
					// console.log(r.message);
					let x2 = page.find(`span[data-label="All Locations"] .tree-label`);
					x2.text(`${x2.text()} - ( ${((flt(r.message[0][0])).toLocaleString('en') + ' Square Meters in Total ')})`);
				}
			});
		}
	},
	onload: function (treeview, node) {
		treeview.make_tree();
	}
};