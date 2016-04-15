# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

def make_stock_entry(**args):
	s = frappe.new_doc("Stock Entry")
	args = frappe._dict(args)
	if args.posting_date:
		s.posting_date = args.posting_date
	if args.posting_time:
		s.posting_time = args.posting_time

	if not args.purpose:
		if args.source and args.target:
			s.purpose = "Material Transfer"
		elif args.source:
			s.purpose = "Material Issue"
		else:
			s.purpose = "Material Receipt"
	else:
		s.purpose = args.purpose

	s.company = args.company or "_Test Company"
	s.purchase_receipt_no = args.purchase_receipt_no
	s.delivery_note_no = args.delivery_note_no
	s.sales_invoice_no = args.sales_invoice_no
	s.difference_account = args.difference_account or "Stock Adjustment - _TC"

	s.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"s_warehouse": args.from_warehouse or args.source,
		"t_warehouse": args.to_warehouse or args.target,
		"qty": args.qty,
		"basic_rate": args.basic_rate,
		"expense_account": args.expense_account or "Stock Adjustment - _TC",
		"conversion_factor": 1.0,
		"cost_center": "_Test Cost Center - _TC",
		"serial_no": args.serial_no
	})

	if not args.do_not_save:
		s.insert()
		if not args.do_not_submit:
			s.submit()
	return s
