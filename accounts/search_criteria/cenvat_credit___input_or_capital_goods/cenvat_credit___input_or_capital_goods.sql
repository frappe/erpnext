SELECT t1.posting_date, t1.bill_no, t1.bill_date, t1.range, t1.name, SUM(CASE WHEN t2.account_head like '%(main_acc_head)s%' THEN t2.tax_amount ELSE 0.00 END),  SUM(CASE WHEN t2.account_head like '%(add_acc_head)s%' THEN t2.tax_amount ELSE 0.00 END),  SUM(CASE WHEN t2.account_head like '%(cvd_acc_head)s%' THEN t2.tax_amount ELSE 0.00 END),  SUM(CASE WHEN t2.account_head like '%(edu_cess_acc_head)s' THEN t2.tax_amount ELSE 0.00 END),  SUM(CASE WHEN t2.account_head like '%(sh_edu_cess_acc_head)s' THEN t2.tax_amount ELSE 0.00 END), t1.`remarks`
 FROM `tabPurchase Receipt` t1, `tabPurchase Tax Detail` t2
 WHERE t2.parent = t1.name
 AND t2.parent = 'Purchase Reciept'
 AND (t2.account_head LIKE '%(main_acc_head)s' and '%(main_acc_head)s%%' or '~~~~'
 OR t2.account_head LIKE '%(add_acc_head)s' and '%(add_acc_head)s%%' or '~~~~'
 OR t2.account_head LIKE '%(cvd_acc_head)s' and '%(cvd_acc_head)s%%' or '~~~~'
 OR t2.account_head LIKE '%(edu_cess_acc_head)s' and '%(edu_cess_acc_head)s%%' or '~~~~'
 OR t2.account_head LIKE '%(sh_edu_cess_acc_head)s%' and '%(sh_edu_cess_acc_head)s%%' or '~~~~')
 AND t1.`posting_date` >= '%(posting_date)s'
 AND t1.`posting_date` <= '%(posting_date1)s'
 AND t1.docstatus =1
 GROUP BY t1.`name`

UNION

SELECT t1.posting_date, t1.bill_no, t1.bill_date, '' AS 'Range', t1.name, SUM(CASE WHEN t2.account like '%(main_acc_head)s%' THEN t2.debit ELSE 0.00 END),  SUM(CASE WHEN t2.account like '%(add_acc_head)s%' THEN t2.debit ELSE 0.00 END),  SUM(CASE WHEN t2.account like '%(cvd_acc_head)s%' THEN t2.debit ELSE 0.00 END),  SUM(CASE WHEN t2.account like '%(edu_cess_acc_head)s' THEN t2.debit ELSE 0.00 END),  SUM(CASE WHEN t2.account like '%(sh_edu_cess_acc_head)s' THEN t2.debit ELSE 0.00 END), t1.`remark`
 FROM `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
 WHERE (t2.debit is not NULL OR t2.debit != '')
 AND t2.debit > 0
 AND t2.parent = t1.name
 AND (t2.account LIKE '%(main_acc_head)s' and '%(main_acc_head)s%%' or '~~~~'
 OR t2.account LIKE '%(add_acc_head)s' and '%(add_acc_head)s%%' or '~~~~'
 OR t2.account LIKE '%(cvd_acc_head)s' and '%(cvd_acc_head)s%%' or '~~~~'
 OR t2.account LIKE '%(edu_cess_acc_head)s' and '%(edu_cess_acc_head)s%%' or '~~~~'
 OR t2.account LIKE '%(sh_edu_cess_acc_head)s%' and '%(sh_edu_cess_acc_head)s%%' or '~~~~') AND t1.`posting_date` >= '%(posting_date)s'
 AND t1.`posting_date` <= '%(posting_date1)s'
 AND t1.docstatus =1
 GROUP BY t1.`name`

ORDER BY `posting_date`,`name`