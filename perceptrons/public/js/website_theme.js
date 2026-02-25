// Copyright (c) 2019, Hash Include Solutions FZC and Contributors
// MIT License. See license.txt

frappe.ui.form.on("Website Theme", {
	validate(frm) {
		let theme_scss = frm.doc.theme_scss;
		if (
			theme_scss &&
			theme_scss.includes("frappe/public/scss/website") &&
			!theme_scss.includes("perceptrons/public/scss/website")
		) {
			frm.set_value("theme_scss", `${frm.doc.theme_scss}\n@import "perceptrons/public/scss/website";`);
		}
	},
});
