// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

frappe.ui.form.on('Website Theme', {
	apply_custom_theme(frm) {
		let custom_theme = frm.doc.custom_theme;
		custom_theme = custom_theme.split('\n');
		if (
			frm.doc.apply_custom_theme
				&& custom_theme.length === 2
				&& custom_theme[1].includes('frappe/public/scss/website')
		) {
			frm.set_value('custom_theme',
				`$primary: #7575ff;\n@import "frappe/public/scss/website";\n@import "erpnext/public/scss/website";`);
		}
	}
});
