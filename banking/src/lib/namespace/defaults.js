frappe.defaults = {
	get_user_default: function (key) {
		let defaults = frappe.boot.user.defaults;
		let d = defaults[key];
		if (!d) {
			key = key.replace(/ /g, "_").toLowerCase();
			d = defaults[key];
		}
		if (Array.isArray(d)) d = d[0];
		return d;
	},
};
