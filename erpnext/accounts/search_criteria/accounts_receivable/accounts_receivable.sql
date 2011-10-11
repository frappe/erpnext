SELECT `tabGL Entry`.`transaction_date`,`tabGL Entry`.`aging_date`,`tabGL Entry`.`account`, `tabGL Entry`.`against_voucher_type`, `tabGL Entry`.`against_voucher`,`tabGL Entry`.`voucher_type`,`tabGL Entry`.`voucher_no`, `tabGL Entry`.remarks
FROM `tabGL Entry`,`tabAccount`
WHERE `tabGL Entry`.`posting_date`>= '%(posting_date)s'
 AND `tabGL Entry`.`posting_date`<= '%(posting_date1)s'
 AND `tabGL Entry`.`account` LIKE '%(account)s%%'
 AND `tabGL Entry`.`company` LIKE '%(company)s%%'
 AND ((`tabGL Entry`.voucher_type = 'Receivable Voucher' and `tabGL Entry`.debit>0) OR `tabGL Entry`.voucher_type = 'Journal Voucher')
 AND `tabGL Entry`.`is_cancelled` = 'No'
 AND `tabAccount`.master_type = 'Customer'
 AND `tabAccount`.name = `tabGL Entry`.account
 ORDER BY `tabGL Entry`.`posting_date`
