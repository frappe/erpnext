// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
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
		return { filters: { is_group: 0 } };
	},

	employee: function() {
		return { query: "erpnext.controllers.queries.employee_query" }
	},

	warehouse: function(doc) {
		return {
			filters: [
				["Warehouse", "company", "in", ["", cstr(doc.company)]],
				["Warehouse", "is_group", "=",0]
				
			]
		}
	}
});

erpnext.queries.setup_queries = function(frm, options, query_fn) {
	var me = this;
	var set_query = function(doctype, parentfield) {
		var link_fields = frappe.meta.get_docfields(doctype, frm.doc.name,
			{"fieldtype": "Link", "options": options});
		$.each(link_fields, function(i, df) {
			if(parentfield) {
				frm.set_query(df.fieldname, parentfield, query_fn);
			} else {
				frm.set_query(df.fieldname, query_fn);
			}
		});
	};

	set_query(frm.doc.doctype);

	// warehouse field in tables
	$.each(frappe.meta.get_docfields(frm.doc.doctype, frm.doc.name, {"fieldtype": "Table"}),
		function(i, df) {
			set_query(df.options, df.fieldname);
		});
}
