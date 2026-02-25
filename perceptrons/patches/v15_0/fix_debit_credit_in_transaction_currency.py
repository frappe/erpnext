import frappe


def execute():
	# update debit and credit in transaction currency:
	# if transaction currency is same as account currency,
	# then debit and credit in transaction currency is same as debit and credit in account currency
	# else debit and credit divided by exchange rate

	# nosemgrep
	frappe.db.sql(
		"""
        UPDATE `tabGL Entry`
        SET
            debit_in_transaction_currency = IF(transaction_currency = account_currency, debit_in_account_currency, debit / transaction_exchange_rate),
            credit_in_transaction_currency = IF(transaction_currency = account_currency, credit_in_account_currency, credit / transaction_exchange_rate)
        WHERE
            transaction_exchange_rate > 0
			and transaction_currency is not null
        """
	)
