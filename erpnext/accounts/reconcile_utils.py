import frappe
from frappe import _, qb
from frappe.query_builder.functions import Sum
from frappe.query_builder.utils import DocType

# New Reconcile Mechanism, proposed by Kitti U.
def create_partial_reconcile_entries(debit_entries, credit_entries, allocated_amount=False):
	if allocated_amount: # From payment allocation
		if len(debit_entries + credit_entries) != 2:
			frappe.throw(_("Allocated amount is not allowed when reconcile more than 2 GL Entries"))
	for dr in debit_entries:
		for cr in credit_entries:
			amount = min(dr.debit, cr.credit, allocated_amount) if allocated_amount else min(dr.debit, cr.credit) 
			pre = frappe.get_doc(
				dict(
					doctype="Partial Reconcile Entry",
					debit_gl_entry=dr.name,
					credit_gl_entry=cr.name,
					amount=amount
				)
			)
			pre.insert()

def get_all_related_gl_entries(gl_list):
	prev_gl_list = gl_list.copy()
	pre_debit_entries = frappe.db.get_all(
		"Partial Reconcile Entry",
		fields=["name", "debit_gl_entry"],
		filters=[dict(credit_gl_entry=("in", gl_list))],
	)
	gl_list += [x["debit_gl_entry"] for x in pre_debit_entries]
	pre_credit_entries = frappe.db.get_all(
		"Partial Reconcile Entry",
		fields=["name", "credit_gl_entry"],
		filters=[dict(debit_gl_entry=("in", gl_list))],
	)
	gl_list += [x["credit_gl_entry"] for x in pre_credit_entries]
	gl_list = list(set(gl_list))
	if len(prev_gl_list) < len(gl_list):
		get_all_related_gl_entries(gl_list)
	pre_list = [x["name"] for x in pre_debit_entries + pre_credit_entries]
	return (gl_list, pre_list)

def get_gl_entries_by_vouchers(vouchers, is_cancelled=0):
	gl_entries = frappe.db.get_all(
		"GL Entry",
		fields=["*"],
		filters=[
			dict(is_cancelled=("=", is_cancelled)),
			dict(is_reconcile=("=", 1)),
			dict(voucher_no=("in", vouchers)),
		],
		order_by="posting_date asc",
	)
	return gl_entries

def mark_full_reconcile(gl_to_reconcile):
	# Recursive scan to get all related gl from partial reconcile entries
	gl_list = list([x.name for x in gl_to_reconcile])
	gl_list, pre_list = get_all_related_gl_entries(gl_list)
	# If all residual are zero we can mark them as Full Reconciled
	glt = qb.DocType("GL Entry")
	residual = (
		qb.from_(glt).select((Sum(glt.residual)).as_("residual"))
		.where((glt.name.isin(gl_list))).run()
	)
	if not residual[0][0]:
		fre = frappe.get_doc(dict(doctype="Full Reconcile Entry")).save()
		for gl in gl_list:
			frappe.db.set_value("GL Entry", gl, "full_reconcile_entry", fre.name)
		for pre in pre_list:
			frappe.db.set_value("Partial Reconcile Entry", pre, "full_reconcile_entry", fre.name)

def reconcile_gl_entries(gl_entries, allocated_amount=False):
	# Validation
	for gl in gl_entries:
		if not gl.is_reconcile:
			frappe.throw(_("GL Entry {0} / Account {1} can not reconcile").format(gl.name, gl.account, ))
	# gl with against voucher, we can match clearer and clearee gl before reconcile
	gl_clearer = list(filter(
		lambda x: x.get("against_voucher") and x.get("against_voucher") != x.get("voucher_no"),
		gl_entries
	))
	gl_entries == list(filter(
		lambda x: not x.get("against_voucher") or x.get("against_voucher") == x.get("voucher_no"),
		gl_entries
	))
	for glc in gl_clearer:
		gl_clearee = list(filter(
			lambda x: x.get("voucher_no") == glc.get("against_voucher"),
			gl_entries
		))
		gl_entries = list(filter(
			lambda x: x.get("voucher_no") != glc.get("against_voucher"),
			gl_entries
		))
		gl_to_reconcile = [glc] + gl_clearee
		reconcile_gl(gl_to_reconcile, allocated_amount=allocated_amount)
	# other gl w/o against voucher, just reconcile as a single group
	reconcile_gl(gl_entries, allocated_amount=allocated_amount)

def reconcile_gl(gl_to_reconcile, allocated_amount=False):
	debit_entries = list(filter(lambda x: x.get("debit"), gl_to_reconcile))
	credit_entries = list(filter(lambda x: x.get("credit"), gl_to_reconcile))
	if len(debit_entries) > 1 and len(credit_entries) > 1:
		frappe.throw(_("Reconcile process only allow either 1 credit or debit entry"))
	# Create partial reconcile entry for each dr/cr pair
	create_partial_reconcile_entries(debit_entries, credit_entries, allocated_amount)
	# Update residual for all gl entries
	for gl in gl_to_reconcile:
		update_gl_residual(gl)
	# Mark a Full Reconcile Entry when all residual reach zero
	if set([x.residual for x in gl_to_reconcile]) == {0}:
		mark_full_reconcile(gl_to_reconcile)

def unreconcile_gl(gl_to_unreconcile):
	# remove full reconcile entry everywhere
	gl_list = [x["name"] for x in gl_to_unreconcile]
	gl_list, pre_list = get_all_related_gl_entries(gl_list)
	for gl in gl_list:
		frappe.db.set_value("GL Entry", gl, "full_reconcile_entry", None)
	for pre in pre_list:
		frappe.db.set_value("Partial Reconcile Entry", pre, "full_reconcile_entry", None)
	# Set amount in parital reconcile entry to zero
	gl_list = [x.name for x in gl_to_unreconcile]
	pre_list = frappe.db.get_all(
		"Partial Reconcile Entry",
		fields=["*"],
		filters=[dict(debit_gl_entry=("in", gl_list))],
	)
	pre_list += frappe.db.get_all(
		"Partial Reconcile Entry",
		fields=["*"],
		filters=[dict(credit_gl_entry=("in", gl_list))],
	)
	for pre in pre_list:
		frappe.db.set_value("Partial Reconcile Entry", pre.name, "amount", 0)
	for pre in pre_list:
		update_gl_residual(frappe.get_doc("GL Entry", pre.debit_gl_entry))
		update_gl_residual(frappe.get_doc("GL Entry", pre.credit_gl_entry))

def update_gl_residual(gl):
	if not gl.is_reconcile:
		return
	if gl.is_cancelled:
		frappe.db.set_value("GL Entry", gl.name, "residual", 0)
		return
	# Begin amount
	gl_amount = gl.debit - gl.credit
	# Used amount
	pre = qb.DocType("Partial Reconcile Entry")
	debit = (
		qb.from_(pre).select((Sum(pre.amount)).as_("total_debit"))
		.where((pre.debit_gl_entry == gl.name)).run()
	)
	credit = (
		qb.from_(pre).select((Sum(pre.amount)).as_("total_credit"))
		.where((pre.credit_gl_entry == gl.name)).run()
	)
	reonciled_amount = (debit[0][0] or 0) - (credit[0][0] or 0)
	# Update Residual
	gl.residual = gl_amount - reonciled_amount
	frappe.db.set_value("GL Entry", gl.name, "residual", gl.residual)
