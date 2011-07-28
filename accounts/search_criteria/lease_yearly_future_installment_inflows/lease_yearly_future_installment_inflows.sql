select year(date_sub(due_date,interval 6 MONTH)) as yr,sum(amount)

from `tabLease Agreement` la,`tabLease Installment` lai

where la.name=lai.parent and (lai.cheque_date is null or lai.cheque_date > '%(date)s')

group by year(date_sub(due_date,interval 6 MONTH))

order by yr