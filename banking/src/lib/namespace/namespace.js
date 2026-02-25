if (!window.frappe) window.frappe = {};

frappe.provide = function (namespace) {
	// docs: create a namespace //
	var nsl = namespace.split(".");
	var parent = window;
	for (var i = 0; i < nsl.length; i++) {
		var n = nsl[i];
		if (!parent[n]) {
			parent[n] = {};
		}
		parent = parent[n];
	}
	return parent;
};

frappe.provide("locals");
frappe.provide("frappe.flags");
frappe.provide("frappe.settings");
frappe.provide("locals.DocType");
frappe.provide("frappe.model");
frappe.provide("frappe.defaults");
