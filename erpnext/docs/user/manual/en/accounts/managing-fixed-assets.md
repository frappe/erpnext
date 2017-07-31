# Managing Fixed Assets

In ERPNext, you can maintain fixed asset records like Computers, Furnitures, Cars, etc. and manage depreciations, sale or disposal of those assets.

## Asset Category

Based on the type of assets, create Asset Category. For example, all your desktops and laptops can be part of an Asset Category named "Computers". Here you can set default depreciation method, periodicity and depreciation related accounts, which will be applicable to all the assets under the category.

<img class="screenshot" alt="Asset Category" src="{{docs_base_url}}/assets/img/accounts/asset-category.png">

> **Note:** You can also set default depreciation related Accounts and Cost Centers in Company master.

## Asset

Asset master is the heart of fixed asset management feature. All the transactions related to Asset like purchasing, sales, depreciation, scrapping will be managed from the Asset master.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset.png">

Explanation of the fields:

1. Item Code: An Item for the Asset must be a non-stock item, with "Is Asset" field checked.

	<img class="screenshot" alt="Asset Item" src="{{docs_base_url}}/assets/img/accounts/asset-item.png">

2. Asset Category: The category of assets it belongs to.
3. Is Existing Asset: Check if the asset is being carried forward from the previous Fiscal Year. The existing assets which are partially / fully depreciated can also be created/maintained for the future reference.
4. Status: The options are - Draft, Submitted, Partially Depreciated, Fully Depreciated, Sold and Scrapped.
5. Warehouse: Set the location of the asset.
6. Gross Purchase Amount: The purchase cost of the asset.
7. Expected Value After Useful Life: Useful Life is the time period over in which the company expects that the asset will be productive. After that period, either the asset is scrapped or sold. In case it is sold, mention the estimated value here. This value is also known as Salvage Value, Scrap Value or Residual Value.
8. Opening Accumulated Depreciation: The accumulated depreciation amount which has already been booked for an existing asset.
9. Current Value (After Depreciation): In case you are creating record of an existing asset which has already been partially/fully depreciated, mention the current value of the asset. In case of new asset, mention the purchase amount or leave it blank.
10. Depreciation Method: There are two options: Straight Line and Double Declining Balance.
	- Straight Line: This method spreads the cost of the fixed asset evenly over its useful life.
	- Double Declining Method: An accelerated method of depreciation, it results in higher depreciation expense in the earlier years of ownership.
10. Total Number of Depreciations: The total number of depreciations during the useful life. In case of existing assets which are partially depreciated, mention the number of pending depreciations.
11. Number of Depreciations Booked: Enter the number of already booked depreciations for an existing asset.
12. Frequency of Depreciation (Months): The number of months between two depreciations.
13. Next Depreciation Date: Mention the next depreciation date, even if it is the first one. If the asset is an existing one and depreciation has already been completed, leave it blank.

### Depreciations

The system automatically creates a schedule for depreciation based on depreciation method and other related inputs in the Asset record.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/depreciation-schedule.png">

On the scheduled date, system creates depreciation entry by creating a Journal Entry and the same Journal Entry is updated in the depreciation table for reference. Next Depreciation Date and Current Value are also updated on submission of depreciation entry.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/depreciation-entry.png">

In the depreciation entry, the "Accumulated Depreciation Account" is credited and "Depreciation Expense Account" is debited. The related accounts can be set in the Asset Category or Company.

For better visibility, net value of the asset on different depreciation dates are shown in a line graph.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset-graph.png">


## Purchase an Asset

For purchasing a new asset, create and submit the asset record with all the depreciation settings. Then create a Purchase Invoice via "Make Purchase Invoice" button. On clicking the button, system will load a new Purchase Invoice form with pre-loaded items table. It will also set proper fixed asset account (defined in the Asset Category) in the Expense Account field. You need to select Supplier and other necessary details and submit the Purchase Invoice.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset-purchase-invoice.png">

On submission of the invoice, the "Fixed Asset Account" will be debited and payable account will be credited. It also updates purchase date, supplier and Purchase Invoice no. in the Asset master.


## Sell an Asset

To sell an asset, open the asset record and create a Sales Invoice by clicking on "Sell Asset". On submission of the Sales Invoice, following entries will take place:

- "Receivable Account" (Debtors) will be debited by the sales amount.
- "Fixed Asset Account" will be credited by the purchase amount of asset.
- "Accumulated Depreciation Account" will be debited by the total depreciated amount till now.
- "Gain/Loss Account on Asset Disposal" will be credited/debited based on gain/loss amount. The Gain/Loss account can be set in Company record.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset-sales.png">


## Scrap an Asset

You can scrap an asset anytime using the "Scrap Asset" button in the Asset record. The "Gain/Loss Account on Asset Disposal" mentioned in the Company is debited by the Current Value (After Depreciation) of the asset. After scrapping, you can also restore the asset using "Restore Asset" button.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/scrap-journal-entry.png">

## Asset Movement

The movement of the assets (from one warehouse to another) is also tracked via Asset Movement form.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset-movement.png">

There is also a dedicated button "Transfer Asset" inside the Asset form to track the Asset Movement.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset-movement-using-button.png">

{next}
