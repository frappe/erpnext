let datatable;
let current_filter_param = "";
let is_fetching = false;
let selected_invoices = [];

const all_invoices_filter = "all";
const week_invoices_filter = "week";
const undue_invoices_filter = "undue";
const one_month_filter = "30";
const two_months_filter = "60";
const three_months_filter = "90";
const four_months_filter = "120";
const oldest_filter = "oldest";

const table_columns = [
	{
		name: `
        <input 
            type="checkbox" 
            id="select-all-checkbox" 
            style="cursor: pointer; transform: scale(1.1);"
            title="Select / Deselect All"
        />
    	`,
		id: "select",
		width: 50,
		editable: false,
		resizable: false,
		dropdown: false,
		format: (value, row, column, data, rowIndex) => {
			return `
				<input 
					type="checkbox" 
					class="invoice-checkbox" 
					data-invoice="${data.name}" 
					style="cursor: pointer;"
				/>
			`;
		},
	},
	{
		name: __("Invoice No."),
		id: "name",
		width: 150,
		editable: false,
		resizable: false,
		format: (value) => `<a href="/app/purchase-invoice/${value}" target="_blank">${value}</a>`,
	},
	{
		name: __("Invoice Date"),
		id: "posting_date",
		width: 120,
		editable: false,
		resizable: false,
		format: (value) => frappe.format(value, { fieldtype: 'Date' }),
	},
	{
		name: __("Party"),
		id: "supplier_name",
		width: 180,
		editable: false,
		resizable: false,
		format: (value) => `<a href="/app/supplier/${value}" target="_blank">${value}</a>`,
	},
	{
		name: __("Payable (Entered)"),
		id: "grand_total",
		width: 160,
		editable: false,
		resizable: false,
		format: (value, _, __, doc) => frappe.format(value, { fieldtype: 'Currency', options: "currency" }, null, doc),
	},
	{
		name: __("Payable (Accounted)"),
		id: "outstanding_amount",
		width: 150,
		editable: false,
		resizable: false,
		format: (value, _, __, doc) => frappe.format(value, { fieldtype: 'Currency', options: "price_list_currency" }, null, doc),
	},
	{
		name: __("GST"),
		id: "base_taxes_and_charges_added",
		width: 150,
		editable: false,
		resizable: false,
		format: (value, _, __, doc) => frappe.format(value, { fieldtype: 'Currency', options: "price_list_currency" }, null, doc),
	},
	{
		name: __("TDS"),
		id: "base_taxes_and_charges_deducted",
		width: 150,
		editable: false,
		resizable: false,
		format: (value, _, __, doc) => frappe.format(value, { fieldtype: 'Currency', options: "price_list_currency" }, null, doc),
	},
	{
		name: __("Due Date"),
		id: "due_date",
		width: 150,
		editable: false,
		resizable: false,
		format: (value) => frappe.format(value, { fieldtype: 'Date' }),
	},
];

const invoice_filters = [
	{
		label: "All",
		fieldname: "all-invoices",
		filterparam: all_invoices_filter,
	},
	{
		label: "Not due yet",
		fieldname: "undue-invoices",
		filterparam: undue_invoices_filter,
	},
	{
		label: "Due this week",
		fieldname: "week-invoices",
		filterparam: week_invoices_filter,
	},
	{
		label: "0 - 30 days old",
		fieldname: "one-month-old",
		filterparam: one_month_filter,
	},
	{
		label: "31 - 60 days old",
		fieldname: "two-months-old",
		filterparam: two_months_filter,
	},
	{
		label: "61 - 90 days old",
		fieldname: "three-months-old",
		filterparam: three_months_filter,
	},
	{
		label: "91 - 120 days old",
		fieldname: "four-months-old",
		filterparam: four_months_filter,
	},
	{
		label: "Older than 120 days",
		fieldname: "very-old",
		filterparam: oldest_filter,
	},
];

let table_data = [];

frappe.pages["outstanding-invoices"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Outstanding Invoices",
		single_column: true,
	});

	page.set_secondary_action("Refresh Invoices", () => refresh_invoices(page), "refresh");
	page.add_action_item("Print", () => open_print_dialog(), true);

	page.set_primary_action("Proceed for Payment", () => {
        if (selected_invoices.length === 0) {
            frappe.msgprint("Please select at least one invoice to proceed for payment.");
            return;
        }

        frappe.confirm(
            `Are you sure you want to proceed payment for ${selected_invoices.length} invoice(s)?`,
            () => {
                frappe.call({
                    method: "erpnext.administration_dashboard.page.outstanding_invoices.outstanding_invoices.process_multiple_payments",
                    args: { invoices: selected_invoices },
                    freeze: true,
                    freeze_message: __("Processing payments..."),
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.msgprint("Payments processed successfully!");
                            refresh_invoices(page);
                            selected_invoices = [];
                        }
                    },
                });
            }
        );
    }, "money");

	const open_print_dialog = () => {
		frappe.msgprint("Work in progress. Coming soon!");
	};

	const filter_buttons = [];

	for (const filter of invoice_filters) {
		var button = page.add_field({
			label: filter.label,
			fieldtype: "Button",
			fieldname: filter.fieldname,
		});

		$(button.wrapper).addClass('filter-button-container');
		$(button.wrapper).find('button').addClass('filter-button');

		button.onclick = () => get_invoices(filter.filterparam, page);
		filter_buttons.push(button);
	}

	let $table_wrapper = $(`<div style="margin-top: 10px;" id="invoice-table"></div>`);
	page.body.append($table_wrapper);

	// Initialize the DataTable
	datatable = new frappe.DataTable($table_wrapper.get(0), {
		inlineFilters: true,
		data: [],
		cellHeight: 35,
		columns: table_columns,
		serialNoColumn: false,
		noDataMessage: "No data found",
		layout: "fixed",
	});

	$(document).on("change", ".invoice-checkbox", function () {
        const invoice = $(this).data("invoice");
        if ($(this).is(":checked")) {
            if (!selected_invoices.includes(invoice)) {
                selected_invoices.push(invoice);
            }
        } else {
            selected_invoices = selected_invoices.filter((inv) => inv !== invoice);
        }
    });

	$(document).on("change", "#select-all-checkbox", function () {
    	const checked = $(this).is(":checked");
    	$(".invoice-checkbox").prop("checked", checked);
		if (checked) {
			selected_invoices = table_data.map((d) => d.name);
		} else {
			selected_invoices = [];
		}
	});

	setTimeout(() => {
		datatable.refresh(table_data, table_columns);
		datatable.setDimensions();
		current_filter_param = invoice_filters[0].filterparam;
		refresh_invoices(page);
	});

	window.addEventListener('resize', () => {
		datatable.refresh(table_data, table_columns);
	}, true);
};

const set_page_title = (page) => {
	const title = "Outstanding Invoices";
	let prefix = "";
	let suffix = "";

	switch (current_filter_param) {
		case all_invoices_filter:
			prefix = "All";
			break;
		case one_month_filter:
			suffix = "Aged 0 - 30 Days";
			break;
		case two_months_filter:
			suffix = "Aged 31 - 60 Days";
			break;
		case three_months_filter:
			suffix = "Aged 61 - 90 Days";
			break;
		case four_months_filter:
			suffix = "Aged 91 - 120 Days";
			break;
		case oldest_filter:
			suffix = "Older Than 120 Days";
			break;
		default:
			break;
	}

	const page_title = __(`${prefix} ${title} ${suffix}`.trim());
	page.set_title(page_title);
};

const refresh_invoices = (page) => {
	get_invoices(current_filter_param, page);
};

const get_invoices = (filter_param, page) => {
	if (is_fetching) {
		return;
	}

	is_fetching = true;
	current_filter_param = filter_param;
	set_page_title(page);
	frappe.call({
		method: "erpnext.administration_dashboard.page.outstanding_invoices.outstanding_invoices.get_invoices",
		args: {
			filter_param,
			start: 1,
			limit: 100,
		},
		freeze: true,
		freeze_message: __('Getting the requested outstanding invoices...'),
		callback: function (r) {
			is_fetching = false;
			if (r && r.message && r.message.length !== undefined) {
				table_data = r.message;
				datatable.refresh(table_data, table_columns);
			} else {
				frappe.throw(r.message.error ?? "Error: Could not get a response from the server.");
			}
		},
	});
};

const filter_invoices = () => {
	refresh_data();
};
