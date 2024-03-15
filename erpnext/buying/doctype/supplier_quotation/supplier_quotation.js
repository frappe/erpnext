// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

erpnext.buying.setup_buying_controller();
erpnext.buying.SupplierQuotationController = class SupplierQuotationController extends (
	erpnext.buying.BuyingController
) {
	setup() {
		this.frm.custom_make_buttons = {
			"Purchase Order": "Purchase Order",
			Quotation: "Quotation",
		};

		super.setup();
	}

	refresh() {
		var me = this;
		super.refresh();

		if (this.frm.doc.__islocal && !this.frm.doc.valid_till) {
			this.frm.set_value("valid_till", frappe.datetime.add_months(this.frm.doc.transaction_date, 1));
		}
		if (this.frm.doc.docstatus === 1) {
			cur_frm.add_custom_button(__("Purchase Order"), this.make_purchase_order, __("Create"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Create"));
			cur_frm.add_custom_button(__("Quotation"), this.make_quotation, __("Create"));
		} else if (this.frm.doc.docstatus === 0) {
			this.frm.add_custom_button(
				__("Material Request"),
				function () {
					erpnext.utils.map_current_doc({
						method: "erpnext.stock.doctype.material_request.material_request.make_supplier_quotation",
						source_doctype: "Material Request",
						target: me.frm,
						setters: {
							schedule_date: undefined,
							status: undefined,
						},
						get_query_filters: {
							material_request_type: "Purchase",
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_ordered: ["<", 100],
							company: me.frm.doc.company,
						},
					});
				},
				__("Get Items From")
			);

			// Link Material Requests
			this.frm.add_custom_button(
				__("Link to Material Requests"),
				function () {
					erpnext.buying.link_to_mrs(me.frm);
				},
				__("Tools")
			);

			this.frm.add_custom_button(
				__("Request for Quotation"),
				function () {
					if (!me.frm.doc.supplier) {
						frappe.throw({ message: __("Please select a Supplier"), title: __("Mandatory") });
					}
					erpnext.utils.map_current_doc({
						method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.make_supplier_quotation_from_rfq",
						source_doctype: "Request for Quotation",
						target: me.frm,
						setters: {
							transaction_date: null,
						},
						get_query_filters: {
							supplier: me.frm.doc.supplier,
							company: me.frm.doc.company,
						},
						get_query_method:
							"erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_rfq_containing_supplier",
					});
				},
				__("Get Items From")
			);
		}
	}

	make_purchase_order() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
			frm: cur_frm,
		});
	}
	make_quotation() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_quotation",
			frm: cur_frm,
		});
	}
};

// for backward compatibility: combine new and previous states
extend_cscript(cur_frm.cscript, new erpnext.buying.SupplierQuotationController({ frm: cur_frm }));

cur_frm.fields_dict["items"].grid.get_field("project").get_query = function (doc, cdt, cdn) {
	return {
		filters: [["Project", "status", "not in", "Completed, Cancelled"]],
	};
};
