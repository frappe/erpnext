SELECT `tabJournal Voucher`.`name`,`tabJournal Voucher Detail`.`account`,`tabJournal Voucher Detail`.`credit`,`tabJournal Voucher Detail`.`debit`,`tabJournal Voucher Detail`.`against_invoice`,`tabJournal Voucher Detail`.`is_advance`,`tabJournal Voucher`.`voucher_date`,`tabJournal Voucher`.`aging_date`,`tabJournal Voucher`.`company`,`tabJournal Voucher`.`cheque_no`,`tabJournal Voucher`.`cheque_date`,`tabCustomer`.`territory`, `tabJournal Voucher`.`remark`
 FROM `tabJournal Voucher Detail`,`tabJournal Voucher`,`tabAccount`,`tabCustomer`
 WHERE `tabJournal Voucher`.docstatus=1
 AND `tabJournal Voucher`.`posting_date`>='%(posting_date)s'
 AND `tabJournal Voucher`.`posting_date`<='%(posting_date1)s'
 AND `tabJournal Voucher`.`company` LIKE '%(company)s%%'
 AND `tabJournal Voucher`.`is_opening` LIKE '%(is_opening)s%%'
 AND `tabJournal Voucher Detail`.`account` LIKE '%(account)s%%'
 AND `tabAccount`.master_type = 'Customer'
 AND `tabAccount`.`account_name` = `tabCustomer`.`name`
 AND `tabJournal Voucher Detail`.`account` = `tabAccount`.`name`
 AND `tabJournal Voucher Detail`.`parent` = `tabJournal Voucher`.`name`
 ORDER BY `tabJournal Voucher`.`name`