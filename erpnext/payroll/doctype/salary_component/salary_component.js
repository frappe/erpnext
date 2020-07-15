// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Component', {
	setup: function(frm) {
		frm.set_query("default_account", "accounts", function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					"is_group": 0,
					"company": d.company
				}
			};
		});
		frm.set_query("earning_component_group", function() {
			return {
				filters: {
					"is_group": 1,
					"is_flexible_benefit": 1
				}
			};
		});
	},
	is_flexible_benefit: function(frm) {
		if(frm.doc.is_flexible_benefit){
			set_value_for_condition_and_formula(frm);
			frm.set_value("formula", '');
			frm.set_value("amount", 0);
		}
	},
	type: function(frm) {
		if(frm.doc.type=="Earning"){
			frm.set_value("is_tax_applicable", 1);
			frm.set_value("variable_based_on_taxable_salary", 0);
		}
		if(frm.doc.type=="Deduction"){
			frm.set_value("is_tax_applicable", 0);
			frm.set_value("is_flexible_benefit", 0);
		}
	},
	variable_based_on_taxable_salary: function(frm) {
		if(frm.doc.variable_based_on_taxable_salary){
			set_value_for_condition_and_formula(frm);
		}
	},
	create_separate_payment_entry_against_benefit_claim: function(frm) {
		if(frm.doc.create_separate_payment_entry_against_benefit_claim){
			frm.set_df_property("accounts", "reqd", 1);
			frm.set_value("only_tax_impact", 0);
		}
		else{
			frm.set_df_property("accounts", "reqd", 0);
		}
	},
	only_tax_impact: function(frm) {
		if(frm.only_tax_impact){
			frm.set_value("create_separate_payment_entry_against_benefit_claim", 0);
		}
	}
});

var set_value_for_condition_and_formula = function(frm) {
	frm.set_value("formula", null);
	frm.set_value("condition", null);
	frm.set_value("amount_based_on_formula", 0);
	frm.set_value("statistical_component", 0);
	frm.set_value("do_not_include_in_total", 0);
	frm.set_value("depends_on_payment_days", 0);
};


frappe.tour['Salary Component'] = [
	{
		fieldname: "salary_component",
		title: "Enter Name",
		description: __("Name you Salary Component"),
	},
	{
		fieldname: "salary_component_abbr",
		title: "Salary Component Abbreviation",
		description: __("Abbreviation for salary components are used during creation of Salary Structure for calculating different component amount in formula and condition section")
	},
	{
		fieldname: "Component Type",
		title: "type",
		description: __("Component Type should be one of deduction or earning ")
	},
	{
		fieldname: "depends_on_payment_days",
		title: "Depends on Payment Days",
		description: __("If this checkbox is enabled then the Salary Component will be calculated based on the number of Payment days.")
	},
	{
		fieldname: "do_not_include_in_total",
		title: "Do Not Include in Total",
		description: __("Selecting this checkbox ensures that the Salary Component is not included in the Total Salary. It is used to define the component which is part of the CTC but not payable.")
	},
	{
		fieldname: "accounts",
		title: "Accounts",
		description: __("Select Accounts For your Salary Component which is used during.")
	},
];