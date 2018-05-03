# Exchange Rate Field Frozen

In ERPNext, you can fetch Exchange Rates between currencies in real-time, or save specific exchange rates as well. In ERPNext, saved exchange rates are also referred as Stale Exchange Rate.

In your sales and purchase transactions, if the field of Currency Exchange Rate is frozen, that is because the feature of allowing stale exchange rates in transactions is enabled. To you wish to make Currency Exchange Rate field editable again, then disable the feature of Stale Exchange Rate from:

* Accounts > Setup > Accounts Settings
* Uncheck field "Allow Stale Exchange Rates".
    <img class="screenshot" alt="Exchange Rate Frozen" src="{{docs_base_url}}/assets/img/accounts/exchange-rate-frozen.png">
* Save Account Settings
* Refresh your ERPNext account
* Check Sales / Purchase transaction once again

After this setting, the Exchange Rate field in the transactions should become editable once again.