const doctype_list = ["Sales Invoice", "Delivery Note", "Purchase Order", "POS Invoice"];
const allowed_print_formats = [
	"Sales Invoice Standard",
	"Sales Invoice with Item Image",
	"Delivery Note Standard",
	"Delivery Note with Item Image",
	"Purchase Order Standard",
	"Purchase Order with Item Image",
	"POS Invoice Standard",
	"POS Invoice with Item Image",
];
const allowed_letterheads = ["Company Letterhead", "Company Letterhead - Grey"];

handle_route_event();

function handle_route_event() {
	const route = frappe.get_route();
	const current_doctype = route[1];
	const current_docname = route[2];

	if (!doctype_list.includes(current_doctype)) return;

	setTimeout(() => {
		if (should_fetch_company_details()) {
			fetch_company_details(current_doctype, current_docname);
		}
	}, 500);
}

function should_fetch_company_details() {
	const print_format = $('input[data-fieldname="print_format"]').val();
	const letterhead = $('input[data-fieldname="letterhead"]').val();

	return allowed_print_formats.includes(print_format) || allowed_letterheads.includes(letterhead);
}

function fetch_company_details(current_doctype, current_docname) {
	frappe.call({
		method: "erpnext.controllers.accounts_controller.get_missing_company_details",
		args: { doctype: current_doctype, docname: current_docname },
		callback: function (r) {
			if (r && r.message) {
				open_company_details_dialog(r.message, current_doctype);
			}
		},
	});
}

function open_company_details_dialog(data, current_doctype) {
	const dialog = new frappe.ui.Dialog({
		title: __("Enter Company Details"),
		fields: build_dialog_fields(data),
		primary_action_label: __("Save"),
		primary_action(values) {
			save_company_details(dialog, data, values, current_doctype);
		},
	});

	dialog.show();
}

function build_dialog_fields(data) {
	return [
		make_field(__("Company Logo"), "company_logo", "Attach Image", data.company_logo),
		make_field(__("Website"), "website", "Data", data.website),
		make_field(__("Phone No"), "phone_no", "Data", data.phone_no),
		{
			label: __("Email"),
			fieldname: "email",
			fieldtype: "Data",
			options: "Email",
			reqd: data.email ? 0 : 1,
			hidden: data.email ? 1 : 0,
		},
		{ fieldtype: "Section Break" },

		make_field(__("Address Title"), "address_title", "Data", data.address_line),
		{
			label: __("Address Type"),
			fieldname: "address_type",
			fieldtype: "Select",
			options: ["Billing", "Shipping"],
			default: "Billing",
			reqd: data.address_line ? 0 : 1,
			hidden: data.address_line ? 1 : 0,
		},
		make_field(__("Address Line 1"), "address_line1", "Data", data.address_line),
		make_field(__("Address Line 2"), "address_line2", "Data", data.address_line, false),
		make_field(__("City"), "city", "Data", data.address_line),
		make_field(__("State"), "state", "Data", data.address_line, false),
		{
			label: __("Country"),
			fieldname: "country",
			fieldtype: "Link",
			options: "Country",
			reqd: data.address_line ? 0 : 1,
			hidden: data.address_line ? 1 : 0,
		},
		make_field(__("Postal Code"), "pincode", "Data", data.address_line, false),

		{
			label: __("Select Company Address"),
			fieldname: "company_address",
			fieldtype: "Link",
			options: "Address",
			get_query: () => ({
				query: "frappe.contacts.doctype.address.address.address_query",
				filters: {
					link_doctype: "Company",
					link_name: data.company,
				},
			}),
			reqd: data.address_line && !data.company_address ? 1 : 0,
			hidden: data.address_line && !data.company_address ? 0 : 1,
		},
	];
}

function make_field(label, fieldname, fieldtype, existing_value, required_if_empty = true) {
	return {
		label,
		fieldname,
		fieldtype,
		reqd: existing_value ? 0 : required_if_empty ? 1 : 0,
		hidden: existing_value ? 1 : 0,
	};
}

function save_company_details(dialog, data, values, current_doctype) {
	frappe.call({
		method: "erpnext.controllers.accounts_controller.update_company_master_and_address",
		args: {
			name: data.name,
			company: data.company,
			details: values,
			current_doctype: current_doctype,
		},
		callback() {
			dialog.hide();
			frappe.msgprint(__("Updating details."));

			setTimeout(() => {
				location.reload();
			}, 1000);
		},
	});
}
