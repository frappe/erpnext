#Adjust Withhold Amount in the Payment Entry

###Question

Let's assume that outstanding against a Sales Invoice is 20,000. When client makes payment, they will only pay 19,600. Rest 400 will be booked under Withhold account. How to manage this scenario in the Payment Entry.

###Answer

In the Payment Entry, you can mention Withhold Account in the Deductions or Loss table. Detailed steps below.

####Step 1: Setup Withhold Account

Create a Withhold Account in your Chart of Accounts master.

`Accounts > Chart of Accounts'

####Step 2: Payment Entry

To create Payment Entry, go to unpaid Sales Invoice and create click on Make Payment button.

#####Step 2.1: Enter Payment Amount

Enter Payment Amount as 19,600.

<img alt="Sales Invoice Payment Amount" class="screenshot" src="{{docs_base_url}}/assets/img/articles/withhold-1.png">

#####Step 2.2: Allocate Against Sales Invoice

Against Sales Invoice, allocate 20,000 (explained in GIF below).

#####Step 2.3: Add Deduction/Loss Account

You can notice that there is a difference of 400 in the Payment Amount and the Amount Allocated against Sales Invoice. You can book this difference account under Withhold Account.

<img alt="Deduction/Loss Account" class="screenshot" src="{{docs_base_url}}/assets/img/articles/withhold-2.gif">

 Following same steps, you can also manage difference availed due to Currency Exchange Gain/Loss.