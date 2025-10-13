let beforePrintHandled = false;

frappe.realtime.on("sales_invoice_before_print", (data) => {
	const route = frappe.get_route();

	if (!beforePrintHandled && route[0] === "print" && route[1] === "Sales Invoice") {
		beforePrintHandled = true;

		let companyDetailsDialog = new frappe.ui.Dialog({
			title: "Enter Company Details",
			fields: [
				{
					label: "Company Logo",
					fieldname: "company_logo",
					fieldtype: "Attach Image",
					reqd: data.company_logo ? 0 : 1,
					hidden: data.company_logo ? 1 : 0,
				},
				{
					label: "Website",
					fieldname: "website",
					fieldtype: "Data",
					hidden: data.website ? 1 : 0,
				},
				{
					label: "Phone No",
					fieldname: "phone_no",
					fieldtype: "Data",
					reqd: data.phone_no ? 0 : 1,
					hidden: data.phone_no ? 1 : 0,
				},
				{
					label: "Email",
					fieldname: "email",
					fieldtype: "Data",
					options: "Email",
					reqd: data.email ? 0 : 1,
					hidden: data.email ? 1 : 0,
				},
				{
					fieldname: "section_break_1",
					fieldtype: "Section Break",
				},
				{
					label: "Address Title",
					fieldname: "address_title",
					fieldtype: "Data",
					reqd: data.address_line ? 0 : 1,
					hidden: data.address_line ? 1 : 0,
				},
				{
					label: "Address Type",
					fieldname: "address_type",
					fieldtype: "Select",
					options: ["Billing", "Shipping"],
					default: "Billing",
					reqd: data.address_line ? 0 : 1,
					hidden: data.address_line ? 1 : 0,
				},
				{
					label: "Address Line 1",
					fieldname: "address_line1",
					fieldtype: "Data",
					reqd: data.address_line ? 0 : 1,
					hidden: data.address_line ? 1 : 0,
				},
				{
					label: "Address Line 2",
					fieldname: "address_line2",
					fieldtype: "Data",
					hidden: data.address_line ? 1 : 0,
				},
				{
					label: "City",
					fieldname: "city",
					fieldtype: "Data",
					reqd: data.address_line ? 0 : 1,
					hidden: data.address_line ? 1 : 0,
				},
				{
					label: "State",
					fieldname: "state",
					fieldtype: "Data",
					hidden: data.address_line ? 1 : 0,
				},
				{
					label: "Country",
					fieldname: "country",
					fieldtype: "Link",
					options: "Country",
					reqd: data.address_line ? 0 : 1,
					hidden: data.address_line ? 1 : 0,
				},
				{
					label: "Postal Code",
					fieldname: "pincode",
					fieldtype: "Data",
					hidden: data.address_line ? 1 : 0,
				},
				{
					label: "Select Company Address",
					fieldname: "company_address",
					fieldtype: "Link",
					options: "Address",
					get_query: function () {
						return {
							query: "frappe.contacts.doctype.address.address.address_query",
							filters: {
								link_doctype: "Company",
								link_name: data.company,
							},
						};
					},
					reqd: data.address_line && !data.company_address ? 1 : 0,
					hidden: data.address_line && !data.company_address ? 0 : 1,
				},
			],
			primary_action_label: "Save",
			primary_action(values) {
				frappe.call({
					method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.save_company_master_details",
					args: {
						name: data.name,
						company: data.company,
						details: values,
					},
					callback: function () {
						companyDetailsDialog.hide();
						frappe.msgprint(__("Updating details."));
						setTimeout(() => {
							window.location.reload();
						}, 1000);
					},
				});
			},
		});
		companyDetailsDialog.show();
	}
});
frappe.router.on("change", () => {
	const route = frappe.get_route();
	if (route[0] !== "print" || route[1] !== "Sales Invoice") {
		beforePrintHandled = false;
	}
});
