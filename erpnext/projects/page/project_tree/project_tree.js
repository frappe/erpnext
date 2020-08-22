frappe.provide('frappe.views');
frappe.provide("erpnext.projects");

frappe.pages['project-tree'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Project Tree',
		single_column: true
	});

	frappe.model.with_doctype("Project", () => {
		frappe.model.with_doctype("Task", () => {
			new erpnext.projects.ProjectTree({
				doctype: "Project",
				parent: wrapper,
				page: page
			});
		});
	});
};