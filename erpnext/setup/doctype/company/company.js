// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.company");

// Static filters (is_group / disabled / warehouse_type) live in the fields' link_filters.
const WAREHOUSE_DEFAULT_FIELDS = [
	"default_warehouse",
	"sample_retention_warehouse",
	"default_in_transit_warehouse",
	"default_warehouse_for_sales_return",
	"default_wip_warehouse",
	"default_fg_warehouse",
	"default_scrap_warehouse",
];

frappe.ui.form.on("Company", {
	onload: function (frm) {
		if (frm.doc.__islocal && frm.doc.parent_company) {
			frappe.db.get_value("Company", frm.doc.parent_company, "is_group", (r) => {
				if (!r.is_group) {
					frm.set_value("parent_company", "");
				}
			});
		}
		if (!frm.doc.__islocal) {
			frm.call("check_if_transactions_exist").then((r) => {
				frm.toggle_enable("default_currency", !r.message);
			});
		}
		if (frm.doc.__islocal) {
			frm.set_value("reporting_currency", "");
		}
	},
	setup: function (frm) {
		frm.__rename_queue = "long";

		frm.set_query("parent_company", function () {
			return {
				filters: { is_group: 1 },
			};
		});

		frm.set_query("default_selling_terms", function () {
			return { filters: { selling: 1, disabled: 0 } };
		});

		frm.set_query("default_sales_contact", function (doc) {
			return {
				query: "frappe.contacts.doctype.contact.contact.contact_query",
				filters: { link_doctype: "Company", link_name: doc.name },
			};
		});

		frm.set_query("default_buying_terms", function () {
			return { filters: { buying: 1, disabled: 0 } };
		});

		WAREHOUSE_DEFAULT_FIELDS.forEach((fieldname) => {
			frm.set_query(fieldname, function (doc) {
				return { filters: { company: doc.name } };
			});
		});

		["default_wip_warehouse", "default_fg_warehouse", "default_scrap_warehouse"].forEach((fieldname) => {
			frm.set_query(fieldname, function (doc) {
				return {
					filters: {
						company: doc.name,
						is_group: 0,
					},
				};
			});
		});

		frm.set_query("default_letter_head", function () {
			return {
				filters: {
					letter_head_for: "DocType",
				},
			};
		});

		frm.set_query("default_letter_head_report", function () {
			return {
				filters: {
					letter_head_for: "Report",
				},
			};
		});
	},

	company_name: function (frm) {
		if (frm.doc.__islocal) {
			// add missing " " arg in split method
			let parts = frm.doc.company_name.split(" ");
			let abbr = $.map(parts, function (p) {
				return p ? p.substr(0, 1) : null;
			}).join("");
			frm.set_value("abbr", abbr);
		}
	},

	parent_company: function (frm) {
		var bool = frm.doc.parent_company ? true : false;
		frm.set_value("create_chart_of_accounts_based_on", bool ? "Existing Company" : "");
		frm.set_value("existing_company", bool ? frm.doc.parent_company : "");
		disbale_coa_fields(frm, bool);
	},

	date_of_commencement: function (frm) {
		if (frm.doc.date_of_commencement < frm.doc.date_of_incorporation) {
			frappe.throw(__("Date of Commencement should be greater than Date of Incorporation"));
		}
		if (!frm.doc.date_of_commencement) {
			frm.doc.date_of_incorporation = "";
		}
	},

	refresh: function (frm) {
		erpnext.company.setup_queries(frm);

		frm.toggle_display("address_html", !frm.is_new());

		if (!frm.is_new()) {
			frm.doc.abbr && frm.set_df_property("abbr", "read_only", 1);
			disbale_coa_fields(frm);
			frappe.contacts.render_address_and_contact(frm);

			if (frappe.perm.has_perm("Cost Center", 0, "read")) {
				frm.add_custom_button(
					__("Cost Centers"),
					function () {
						frappe.set_route("Tree", "Cost Center", { company: frm.doc.name });
					},
					__("View")
				);
			}

			if (frappe.perm.has_perm("Account", 0, "read")) {
				frm.add_custom_button(
					__("Chart of Accounts"),
					function () {
						frappe.set_route("Tree", "Account", { company: frm.doc.name });
					},
					__("View")
				);
			}

			if (frappe.perm.has_perm("Sales Taxes and Charges Template", 0, "read")) {
				frm.add_custom_button(
					__("Sales Tax Template"),
					function () {
						frappe.set_route("List", "Sales Taxes and Charges Template", {
							company: frm.doc.name,
						});
					},
					__("View")
				);
			}

			if (frappe.perm.has_perm("Purchase Taxes and Charges Template", 0, "read")) {
				frm.add_custom_button(
					__("Purchase Tax Template"),
					function () {
						frappe.set_route("List", "Purchase Taxes and Charges Template", {
							company: frm.doc.name,
						});
					},
					__("View")
				);
			}

			if (frm.has_perm("write")) {
				frm.add_custom_button(
					__("Create Tax Template"),
					function () {
						frm.trigger("make_default_tax_template");
					},
					__("Manage")
				);
			}

			if (frappe.user.has_role("System Manager")) {
				if (frm.has_perm("write")) {
					frm.add_custom_button(
						__("Delete Transactions"),
						function () {
							frm.trigger("delete_company_transactions");
						},
						__("Manage")
					);
				}
			}
		}

		if (frm.doc.__islocal) {
			frm.set_value("reporting_currency", "");
		}

		erpnext.company.set_chart_of_accounts_options(frm);
	},

	validate: function (frm) {
		// rows added by "Add Missing Purposes" that got no account
		(frm.doc.default_accounts || [])
			.filter((row) => !row.account)
			.forEach((row) => frappe.model.clear_doc(row.doctype, row.name));
		frm.refresh_field("default_accounts");
	},

	make_default_tax_template: function (frm) {
		frm.call({
			method: "create_default_tax_template",
			doc: frm.doc,
			freeze: true,
			callback: function () {
				frappe.msgprint(__("Default tax templates for sales, purchase and items are created."));
			},
		});
	},

	country: function (frm) {
		erpnext.company.set_chart_of_accounts_options(frm);
	},

	delete_company_transactions: function (frm) {
		frappe.call({
			method: "erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.is_deletion_doc_running",
			args: {
				company: frm.doc.name,
			},
			freeze: true,
			callback: function (r) {
				if (!r.exc) {
					var d = frappe.prompt(
						{
							fieldtype: "Data",
							fieldname: "company_name",
							label: __("Please enter the company name to confirm"),
							reqd: 1,
							description: __(
								"Please make sure you really want to delete all the transactions for {0}. Your master data will remain as it is. Naming series counters will not be reset. This action cannot be undone.",
								[frappe.utils.bold(frm.doc.name)]
							),
						},
						function (data) {
							if (data.company_name !== frm.doc.name) {
								frappe.msgprint(__("Company name does not match"));
								return;
							}
							frappe.call({
								method: "erpnext.setup.doctype.company.company.create_transaction_deletion_request",
								args: {
									company: data.company_name,
								},
								freeze: true,
								callback: function (r, rt) {},
								onerror: function () {
									frappe.msgprint(__("Wrong Password"));
								},
							});
						},
						__("Delete all the Transactions for {0}", [frappe.utils.bold(frm.doc.name)]),
						__("Delete")
					);
					d.get_primary_btn().addClass("btn-danger");
				}
			},
		});
	},
});

erpnext.company.set_chart_of_accounts_options = function (frm) {
	var selected_value = frm.doc.chart_of_accounts;
	if (frm.doc.country) {
		return frappe.call({
			method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
			args: {
				country: frm.doc.country,
				with_standard: true,
			},
			callback: function (r) {
				if (!r.exc) {
					set_field_options("chart_of_accounts", [""].concat(r.message).join("\n"));
					if (r.message.includes(selected_value))
						frm.set_value("chart_of_accounts", selected_value);
				}
			},
		});
	}
};

erpnext.company.setup_queries = function (frm) {
	["cost_center", "round_off_cost_center", "depreciation_cost_center"].forEach((fieldname) => {
		erpnext.company.set_custom_query(frm, [fieldname, {}]);
	});

	erpnext.company.get_purpose_options().then((purposes) => {
		erpnext.company.setup_default_accounts(frm, purposes);
	});
};

erpnext.company.get_purpose_options = function () {
	if (!erpnext.company.purpose_options) {
		erpnext.company.purpose_options = frappe.xcall(
			"erpnext.accounts.default_accounts.get_purpose_options"
		);
	}
	return erpnext.company.purpose_options;
};

erpnext.company.setup_default_accounts = function (frm, purposes) {
	// the purpose stores the key, for example "RECEIVABLE", and shows the label
	const purpose_options = purposes.map((purpose) => ({
		value: purpose.value,
		label: purpose.label,
		description: purpose.description,
	}));
	const labels = Object.fromEntries(purposes.map((purpose) => [purpose.value, purpose.label]));
	frappe.meta.get_docfield("Company Default Account", "purpose").formatter = (value) =>
		labels[value] || value;

	const grid = frm.fields_dict.default_accounts.grid;
	grid.update_docfield_property("purpose", "options", purpose_options);
	frm.refresh_field("default_accounts");

	frm.set_query("account", "default_accounts", function (doc, cdt, cdn) {
		const row = locals[cdt][cdn];
		const purpose = purposes.find((purpose) => purpose.value === row.purpose);
		return {
			filters: { company: doc.name, is_group: 0, ...(purpose ? purpose.filters : {}) },
		};
	});

	if (!frm.is_new() && frm.has_perm("write")) {
		grid.add_custom_button(__("Add Missing Purposes"), () => {
			const existing = new Set((frm.doc.default_accounts || []).map((row) => row.purpose));
			purposes
				.filter((purpose) => !existing.has(purpose.value))
				.forEach((purpose) => frm.add_child("default_accounts", { purpose: purpose.value }));
			frm.refresh_field("default_accounts");
		});
	}
};

erpnext.company.set_custom_query = function (frm, v) {
	var filters = {
		company: frm.doc.name,
		is_group: 0,
	};

	for (var key in v[1]) {
		filters[key] = v[1][key];
	}

	frm.set_query(v[0], function () {
		return {
			filters: filters,
		};
	});
};

var disbale_coa_fields = function (frm, bool = true) {
	frm.set_df_property("create_chart_of_accounts_based_on", "read_only", bool);
	frm.set_df_property("chart_of_accounts", "read_only", bool);
	frm.set_df_property("existing_company", "read_only", bool);
};
