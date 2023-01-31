// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["e-Payment Report"] = {
	"onload": function (query_report) {
    	query_report.filters_by_name.party.toggle(false);
    },
	"filters": [
		{
            fieldname: "payment_type",
            label: "Payment Type",
            fieldtype: "Select",
            options: ["Bank Payment", "Utility Bill Payment"],
            default: "Bank Payment",
            on_change: function(query_report){
                var payment_type = query_report.get_values().payment_type;
                var transaction_type = query_report.filters_by_name["transaction_type"];
                var supplier = query_report.filters_by_name["supplier"];
                var status = query_report.filters_by_name["status"];
                var party = query_report.filters_by_name['party'];

                if (payment_type == 'Utility Bill Payment'){
                    transaction_type.toggle(false);
                    supplier.toggle(false);
                    status.toggle(false);
                    party.toggle(true);
                }
                else{
                    transaction_type.toggle(true);
                    supplier.toggle(true);
                    status.toggle(true);
                    party.toggle(false);
                }
                query_report.refresh()
                transaction_type.refresh()
                supplier.refresh()
                status.refresh()
                party.refresh()
            }
        },
        {
            fieldname: "transaction_type",
            label: "Transaction Type",
            fieldtype: "Select",
            options: ["","Direct Payment", "Journal Entry", "Payment Entry", "Transporter Payment", "Overtime Application", "EME Payment", "Salary Slip", "Employee Loan Payment", "LTC", "Bonus", "PBVA"]
        },
        {
            fieldname: "supplier",
            label: "Supplier",
            fieldtype: "Link",
            options: "Supplier"
        },
        {
            fieldname: "status",
            label: "Status",
            fieldtype: "Select",
            options:["","Completed", "Pending", "Draft", "Waiting for Verification", "Waiting Approval", "Approved", "Rejected", "Failed", "Partial Payment", "Cancelled", "In progress", "Upload Failed", "Waiting Acknowledgement", "Processing Acknowledgement"]
        },
        {
            fieldname: "party",
            label: "Party",
            fieldtype: "Link",
            options: "Supplier"
        },
        {
            fieldname: "branch",
            label: "Branch",
            fieldtype: "Link",
            options: "Branch"
        }

	]
};
