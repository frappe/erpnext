// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch("customer", "customer_group", "customer_group" );

this.frm.toggle_reqd("sales_tax_template", this.frm.doc.tax_type=="Sales");
this.frm.toggle_reqd("purchase_tax_template", this.frm.doc.tax_type=="Purchase");