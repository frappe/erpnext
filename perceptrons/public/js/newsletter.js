// Copyright (c) 2019, Hash Include Solutions FZC and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Newsletter", {
	refresh() {
		perceptrons.toggle_naming_series();
	},
});
