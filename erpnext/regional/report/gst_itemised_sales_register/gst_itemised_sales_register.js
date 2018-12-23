// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include "erpnext/accounting/report/item_wise_sales_register/item_wise_sales_register.js" %}

frappe.query_reports["GST Itemised Sales Register"] = frappe.query_reports["Item-wise Sales Register"]