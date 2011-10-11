SELECT t1.posting_date, t1.bill_no, t1.bill_date, t1.name, SUM(CASE WHEN t2.account like '%(main_acc_head)s%' THEN t2.debit ELSE 0.00 END), SUM(CASE WHEN t2.account like '%(edu_cess_acc_head)s' THEN t2.debit ELSE 0.00 END),  SUM(CASE WHEN t2.account like '%(sh_edu_cess_acc_head)s' THEN t2.debit ELSE 0.00 END), t1.`remark`
 FROM `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
 WHERE (t2.debit is not NULL OR t2.debit != '')
 AND t2.debit > 0
 AND t2.parent = t1.name
 AND (t2.account LIKE '%(main_acc_head)s%%'
 OR t2.account LIKE '%(edu_cess_acc_head)s%%'
 OR t2.account LIKE '%(sh_edu_cess_acc_head)s%%') 
 AND t1.`posting_date` >= '%(posting_date)s'
 AND t1.`posting_date` <= '%(posting_date1)s'
 AND t1.docstatus =1
 GROUP BY t2.`parent`
 ORDER BY t1.`posting_date`,t1.`name`