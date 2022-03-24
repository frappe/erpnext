import frappe


def execute():
	# fixes status of quotations which have status 'Expired' despite having valid sales order created

	# filter out submitted expired quotations which has sales order created
	cond = "qo.docstatus = 1 and qo.status = 'Expired'"
	invalid_so_against_quo = """
		SELECT
			so.name FROM `tabSales Order` so, `tabSales Order Item` so_item
		WHERE
			so_item.docstatus = 1 and so.docstatus = 1
			and so_item.parent = so.name
			and so_item.prevdoc_docname = qo.name
			and qo.valid_till < so.transaction_date""" # check if SO was created after quotation expired

	frappe.db.sql(
		"""UPDATE `tabQuotation` qo SET qo.status = 'Expired' WHERE {cond} and exists({invalid_so_against_quo})"""
			.format(cond=cond, invalid_so_against_quo=invalid_so_against_quo)
		)

	valid_so_against_quo = """
		SELECT
			so.name FROM `tabSales Order` so, `tabSales Order Item` so_item
		WHERE
			so_item.docstatus = 1 and so.docstatus = 1
			and so_item.parent = so.name
			and so_item.prevdoc_docname = qo.name
			and qo.valid_till >= so.transaction_date""" # check if SO was created before quotation expired

	frappe.db.sql(
		"""UPDATE `tabQuotation` qo SET qo.status = 'Closed' WHERE {cond} and exists({valid_so_against_quo})"""
			.format(cond=cond, valid_so_against_quo=valid_so_against_quo)
		)
