// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accounts Settings', {
	refresh: function(frm) {

	}
});

frappe.tour['Accounts Settings'] = [
	{
		fieldname: "acc_frozen_upto",
		title: "Accounts Frozen Upto",
		description: __("Freeze accounting transactions up to specified date, nobody can make/modify entry except the specified Role."),
	},
	{
		fieldname: "frozen_accounts_modifier",
		title: "Role Allowed to Set Frozen Accounts & Edit Frozen Entries",
		description: __("Users with this Role are allowed to set frozen accounts and create/modify accounting entries against frozen accounts.")
	},
	{
		fieldname: "determine_address_tax_category_from",
		title: "Determine Address Tax Category From",
		description: __("Tax category can be set on Addresses. An address can be Shipping or Billing address. Set which addres to select when applying Tax Category.")
	},
	{
		fieldname: "over_billing_allowance",
		title: "Over Billing Allowance Percentage",
		description: __("The percentage by which you can overbill transactions. For example, if the order value is $100 for an Item and percentage here is set as 10% then you are allowed to bill for $110.")
	},
	{
		fieldname: "credit_controller",
		title: "Credit Controller",
		description: __("Select the role that is allowed to submit transactions that exceed credit limits set. The credit limit can be set in the Customer form.")
	},
	{
		fieldname: "make_payment_via_journal_entry",
		title: "Make Payment via Journal Entry",
		description: __("When checked, if user proceeds to make payment from an invoice, the system will open a Journal Entry instead of a Payment Entry.")
	},
	{
		fieldname: "unlink_payment_on_cancellation_of_invoice",
		title: "Unlink Payment on Cancellation of Invoice",
		description: __("If checked, system will unlink the payment against the respective invoice.")
	},
	{
		fieldname: "unlink_advance_payment_on_cancelation_of_order",
		title: "Unlink Advance Payment on Cancellation of Order",
		description: __("Similar to the previous option, this unlinks any advance payments made against Purchase/Sales Orders.")
	}
];
