// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Social Media Post', {
	refresh: async function(frm) {
		let twitter_settings = await frappe.get_doc("Twitter Settings");
		let linkedin_settings = await frappe.get_doc("LinkedIn Setttings");

		frm.toggle_display("twitter", twitter_settings.oauth_token);
		frm.toggle_display("linkedin", linkedin_settings.person_urn);
	}
});
