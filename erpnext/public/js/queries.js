// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// searches for enabled users
frappe.provide("erpnext.queries");
$.extend(erpnext.queries, {
	user: function() {
		return { query: "frappe.core.doctype.user.user.user_query" };
	},

	lead: function() {
		return { query: "erpnext.controllers.queries.lead_query" };
	},

	customer: function() {
		return { query: "erpnext.controllers.queries.customer_query" };
	},

	supplier: function() {
		return { query: "erpnext.controllers.queries.supplier_query" };
	},

	item: function(filters) {
		var args = { query: "erpnext.controllers.queries.item_query" };
		if(filters) args["filters"] = filters;
		return args;
	},

	bom: function() {
		return { query: "erpnext.controllers.queries.bom" };
	},

	task: function() {
		return { query: "erpnext.projects.utils.query_task" };
	},

	customer_filter: function(doc) {
		if(!doc.customer) {
			frappe.throw(__("Please specify a") + " " +
				__(frappe.meta.get_label(doc.doctype, "customer", doc.name)));
		}

		return { filters: { customer: doc.customer } };
	},

	supplier_filter: function(doc) {
		if(!doc.supplier) {
			frappe.throw(__("Please specify a") + " " +
				__(frappe.meta.get_label(doc.doctype, "supplier", doc.name)));
		}

		return { filters: { supplier: doc.supplier } };
	},

	lead_filter: function(doc) {
		if(!doc.lead) {
			frappe.throw(__("Please specify a") + " " +
				__(frappe.meta.get_label(doc.doctype, "lead", doc.name)));
		}

		return { filters: { lead: doc.lead } };
	},

	not_a_group_filter: function() {
		return { filters: { is_group: "No" } };
	},

	employee: function() {
		return { query: "erpnext.controllers.queries.employee_query" }
	},

	warehouse: function(doc) {
		return {
			filters: [["Warehouse", "company", "in", ["", cstr(doc.company)]]]
		}
	}
});
