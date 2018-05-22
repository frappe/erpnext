# How To Manage Subscriptions With ERPNext

ERPNext now allows you to manage your subscriptions easily. A single subscription can contain multiple plans. At 
the same time, A single subscriber can also have multiple subscriptions. ERPNext also automatically manages your 
subscriptions for you by generating new invoices when due and changing the subscription status for you.

## Related Doctypes
### Subscriber
Like its name suggests, the Subscriber Doctype represents your subscribers and each record is linked to a single
Customer.

<img alt="Subscriber form" class="screenshot" src="{{docs_base_url}}/assets/img/articles/subscriber.png">

### Subscription Plan
Each Subscription Plan is linked to a single Item and contains billing and pricing information on the Item. You can have 
multiple Subscription Plans for a single Item. An example of a situation where you would want this is where you have 
different prices for the same Item like when you have a basic option and premium option for a service.

<img alt="Subscription Plan Form" class="screenshot" src="{{docs_base_url}}/assets/img/articles/subscription-plan.png">

### Subscription Settings
Subscription Settings is where you tweak the behaviour of the Subscription Doctype. For example, you can set a grace 
period for overdue invoices from it. You can also elect to have a subscription cancelled if an overdue invoice is not 
paid after the grace period.

<img alt="Subscription Settings Form" class="screenshot" src="{{docs_base_url}}/assets/img/articles/subscription-settings.png">

## Creating A Subscription
To create a Subscription, go to the Subscription creation form
`Explore > Accounts > Subscriptions`

<img alt="Subscription form" class="screenshot" src="{{docs_base_url}}/assets/img/articles/subscription-1.png">

Select a Subscriber.

If you want to cancel a subscription at the end of the present billing cycle, check the 'Cancel At End Of Period' 
check box.

Select the start date for the subscription. By default, the start date is today's date. (Optional).

If you are giving the subscriber a trial, enter the Trial Period Start Date and Trial Period End Date.

If your invoice is not payable immediately, you can set the number of days before the invoice will be due in the 
'Days Until Due' field.

If you require more than one unit of a plan, set it in the 'Quantity' field. For instance, a web developer is subscribed 
to your web hosting service. The developer buys a plan for each customer. Instead of having multiple subscriptions for 
the same plan, you can simply increase the quantity as needed.

In the 'Plan' table, add Subscription Plans as required. You may have multiple Subscription Plans in a single 
Subscription as long as they all have the same billing period cycle. If the same Subscriber needs to subscribe to 
plans with different billing cycles, you will have to use a separate subscription.

Select a Sales Taxes and Charges Template if you need to charge tax in your invoices.

Fill the relevant fields in the 'Discounts' section if you need to add discounts to your invoices.

Click Save.

### Subscription Status
ERPNext Subscription has five status values:
- **Trialling** - A subscription that is in trial period
- **Active** - A subscription that does not have any unpaid invoice
- **Past Due** -  A subscription whose most recent invoice is unpaid but is still within the grace period
- **Unpaid** - A subscription whose most recent invoice is unpaid and past the grace period
- **Canceled** - A subscription whose most recent invoice is unpaid and past the grace period. In this state, ERPNext no longer monitors the subscription.

### Subscription Processing In The Background
Every one hour interval, ERPNext processes all Subscriptions and updates each for any change in status. It will 
create new invoices if need be. When an outstanding invoice is paid, ERPNext updates the subscription accordingly.

### Manually Updating Subscriptions
Once you have saved a subscription, you can change the 'Days Until Due', 'Quantity', 'Plans', 'Sales Taxes and Charges 
Template', 'Apply Additional Discount On', 'Additional Discount Percentage' and 'Additional Discount Amount' fields.

Note that changing any of the values will reflect in newly generated invoices only. Previously generated invoices will 
not be changed.

### Cancelling Subscriptions
To cancel a Subscription, simply click the 'Cancel Subscription' button. The subscription will update its 'Cancellation 
Date' field and the subscription will no longer be monitored.

If you are cancelling an active subscription, an invoice will immediately be generated. The generated invoice will be on 
pro-rata basis by default. If you want ERPNext always create an invoice for the full amount, uncheck the 'Prorate' field 
in Subsciption Settings.

### Restarting Subscriptions
To restart a canceled subscription, simply click the 'Restart Subscription' button. Note the Subscription will empty 
its invoices table. Note that the invoices will still exist but the Subscription will no longer track them. The start 
date of the subscription will also be changed to the date the Subscription is restarted. The start of the billing 
cycle will also be set to the date the Subscription is restarted.

### Recalculating Subscriptions
Some times, a Subscription's status might have changed but might not yet be reflected in the Subscription. You can force 
ERPNext to update the subscription by clicking 'Fetch Subscription Updates'.

### Subscription Settings
**Grace Period** represents the number of days after a subscriber's invoice becomes overdue that ERPNext should delay 
before changing the Subscription status to 'Canceled' or 'Unpaid'.

**Cancel Invoice After Grace Period** would cause ERPNext to automatically cancel a subscription if it is not paid before the grace period elapses. This setting is off by default.

**Prorate** would cause ERPNext to generate a prorated invoice when an active subscription is canceled by default. 
If you would prefer a full invoice, uncheck the setting.