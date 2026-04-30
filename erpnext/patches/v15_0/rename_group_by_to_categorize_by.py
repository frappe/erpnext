import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	rename_field("Process Statement Of Accounts", "group_by", "categorize_by")

	frappe.db.sql(
		"""
		UPDATE
    		`tabProcess Statement Of Accounts`
		SET
			categorize_by = CASE
				WHEN categorize_by = 'Group by Voucher (Consolidated)' THEN 'Categorize by Voucher (Consolidated)'
				WHEN categorize_by = 'Group by Voucher' THEN 'Categorize by Voucher'
			END
		WHERE
			categorize_by IN ('Group by Voucher (Consolidated)', 'Group by Voucher')
	"""
	)
