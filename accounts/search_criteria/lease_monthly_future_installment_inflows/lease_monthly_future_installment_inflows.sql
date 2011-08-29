select date_format(due_date,'%M') as mnt,year(due_date),sum(amount)

from `tabLease Agreement` la,`tabLease Installment` lai

where la.name=lai.parent and (lai.cheque_date is null or lai.cheque_date > '%(date)s')

group by date_format(due_date,'%M-%Y')

order by year(due_date),month(due_date)