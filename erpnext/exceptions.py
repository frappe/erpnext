import frappe


# accounts
class PartyFrozen(frappe.ValidationError):
	pass


class InvalidAccountCurrency(frappe.ValidationError):
	pass


class InvalidCurrency(frappe.ValidationError):
	pass


class PartyDisabled(frappe.ValidationError):
	pass


class InvalidAccountDimensionError(frappe.ValidationError):
	pass


class MandatoryAccountDimensionError(frappe.ValidationError):
	pass
<<<<<<< HEAD


class ReportingCurrencyExchangeNotFoundError(frappe.ValidationError):
	pass
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
