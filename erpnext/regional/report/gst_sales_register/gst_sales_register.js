// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include "erpnext/accounting/report/sales_register/sales_register.js" %}

frappe.query_reports["GST Sales Register"] = frappe.query_reports["Sales Register"]
