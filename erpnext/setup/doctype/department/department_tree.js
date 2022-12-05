frappe.treeview_settings["Department"] = {
	ignore_fields:["parent_department"],
	get_tree_nodes: 'erpnext.setup.doctype.department.department.get_children',
	add_tree_node: 'erpnext.setup.doctype.department.department.add_node',
	filters: [
		{
			fieldname: "company",
			fieldtype:"Link",
			options: "Company",
			label: __("Company"),
		},
	],
	field: ["department_name", "is_division"],
	breadcrumb: "HR",
	root_label: "All Departments",
	get_tree_root: true,
	menu_items: [
		{
			label: __("New Department"),
			action: function() {
				frappe.new_doc("Department", true);
			},
			condition: 'frappe.boot.user.can_create.indexOf("Department") !== -1'
		}
	],
	onload: function(treeview) {
		treeview.make_tree();
	},
	onrender: function(node){
		get_identifier(node)
		// get_employee_count(node);
	},
};

function get_identifier(node){
	let label = ''
	if(node.data.value == 'Chief Executive Officer'){
		label = 'CEO'
	}
	frappe.call({
		method: "erpnext.setup.doctype.department.department.get_employee_count",
		args: {
			department: node.data.value
		},
		callback: function(r){
			let format_string1 = ""
			let format_string2 = ""
			let format_string3 = ""
			let border1 = "3px 0px 0px 3px"
			let border2 = "3px 3px 3px 3px"
			console.log(r.message)
			if (r.message.approver_level) {
				format_string1 = `<span class="badge badge-light" style="font-size:xx-small; margin-left: 5px; border-right: 1px solid grey; border-radius: 3px 0px 0px 3px; background-color: #f68446">${r.message.approver_level}</span>`;
				border1 = "0px 0px 0px 0px"
			}
			if (r.message.approver_name) {
				format_string2 = `<span class="badge badge-light" style="font-size:xx-small; border-right: 1px solid grey; border-radius: ${border1}; background-color: #e5c9f7">${r.message.approver_name}</span>`;
				border2 = "0px 3px 3px 0px"
			}
			if (r.message.count) {
				format_string3 = `<span class="badge badge-light" style="font-size:xx-small; border-radius: ${border2}; background-color: gold">${r.message.count}</span>`;
				console.log("here"+String(node.data.value)+String(r.message.count))
			}
			node.$tree_link.after(format_string1+format_string2+format_string3)

		}
	})
	
}
