frappe.pages['onboarding'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		single_column: true
	});

	frappe.call({
		"method": "erpnext.setup.page.onboarding.onboarding.get_onboarding_data",
		"callback": function(data) {
			frappe.require('onboarding.bundle.js').then(() => {
				let module_data = data.message.workspaces;
				let regional_data = data.message.regional_data;
				let language = data.message.language;
				new erpnext.ui.Onboarding({ wrapper: page.main, page, module_data, regional_data, language});
			})
		}
	})
}