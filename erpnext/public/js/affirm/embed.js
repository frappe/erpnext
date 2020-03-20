/* global cart:false frappe:false */
frappe.provide("frappe.gateway_selector");

frappe.gateway_selector.affirm_embed = frappe.gateway_selector._generic_embed.extend({
    init: function (addressForm, formData) {
        this.gateway = {
            label: "Affirm",
            name: "affirm",
            muteProcessingCallback: true
        };
        this.addressForm = addressForm;
        this.formData = formData;
    },

    collect_billing_info: function () {
        var billing_info = {};
        // collect billing field values

        var result = this.addressForm.validate();
        billing_info = $.extend({}, result.address);

        return billing_info;
    },

    collect: function () {
        this.process_data = {
            billing_info: this.collect_billing_info()
        };
    },

    getSummary: function () {
        this.collect();

        return frappe.render(
            frappe.templates.affirm_gateway_summary, 
            Object.assign({}, this.process_data));
    },

    validate: function () {
        this.collect();
        var valid = true;
        var error = {};
        var address = {};

        if (this.process_data.billing_info) {
            if (!this.process_data.billing_info.address_1) {
                valid = false;
                error['bill_line1'] = "Address line 1 is required";
            }

            if (!this.process_data.billing_info.city) {
                valid = false;
                error['bill_city'] = "City is required";
            }

            if (!this.process_data.billing_info.pincode) {
                valid = false;
                error['bill_pincode'] = "Postal Code is required";
            }

            if (!this.process_data.billing_info.country) {
                valid = false;
                error['bill_country'] = "Postal Code is required";
            }

            // copy address for awc
            for (var key in this.process_data.billing_info) {
                if ({}.hasOwnProperty.call(this.process_data.billing_info, key)) {
                    address[key] = this.process_data.billing_info[key];
                }
            }
        } else {
            valid = false;
        }

        return {
            valid: valid,
            errors: error,
            address: address
        };
    }
});