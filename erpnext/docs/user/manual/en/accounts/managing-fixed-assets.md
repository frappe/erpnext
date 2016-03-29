In ERPNext, you can maintain your fixed asset records like Computers, Building, Cars etc and manage depreciations, sell or disposal of those assets.

## Asset Category

To start first you should create Asset Category, depending on the type of assets. For example, all your desktops and laptops can be part of a Asset Category named "Computers". Here, you can set default depreciation method, periodicity and depreciation related accounts, which will be applicable to all the assets under the category.

<img class="screenshot" alt="Asset Category" src="{{docs_base_url}}/assets/img/accounts/asset-category.png">

> **Note:** You can also set default depreciation related Accounts and Cost Centers in Company.


## Asset

Next step will be creating the fixed asset records. The assets which are partially / fully depreciated can also be created/maintained for the future reference.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset.png">

Explanation of the fields:

1. Asset Category: The category of assets it belongs to.
2. Item Code: The item/product code for the asset, which must be marked as a fixed asset and a non-stock item.
3. Status: The options are - Draft, Submitted, Partially Depreciated, Fully Depreciated, Sold and Scrapped.
4. Gross Purchase Amount: The purchase cost of the asset
5. Expected Value After Useful Life: Useful Life is the time period over in which the company expects that the asset will be productive. After that period, either the asset is scrapped or sold. In case it is sold, mention the estimated value here. This value is also known as Salvage Value, Scrap Value or Residual Value.
6. Current Value (After Depreciation): In case you are creating record of an existing asset which has already been partially/fully depreciated, mention the currect value of the asset. In case of new asset, mention the purchase amount or leave it blank.
7. Depreciation Method: There are two options: Straight Line and Double Declining Balance.
	- Straight Line: This method spreads the cost of the fixed asset evenly over its useful life.
	- Double Declining Method: An accelerated method of depreciation, it results in higher depreciation expense in the earlier years of ownership.
8. Number of Depreciations: The number of depreciations during the useful life. In case of existing assets which are partially depreciated, mention the number of pending depreciations.
9. Number of Months in a Period: The number of months between two depreciations.
10. Next Depreciation Date: Mention the next depreciation date, even if it is the first one. If depreciation already completed, leave it blank.

### Depreciations

The system automatically creates a schedule for depreciation based on depreciation method and other related inputs in the Asset record.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/depreciation-schedule.png">

On the scheduled date, system creates depreciation entry by creating a Journal Entry and the same Journal Entry is updated in the depreciation table for reference. Next Depreciation Date and Current Value are also updated on submission of depreciation entry.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/depreciation-entry.png">

In the depreciation entry, the "Accumulated Depreciation Account" is credited and "Depreciation Expense Account" is debited. The related accounts can be set in the Asset Category or Company.


## Purchase an asset

For purchasing an asset, first create an item for the asset with "Is Fixed Asset" checked. Then create a Purchase Invoice against that item. In the Purchase Invoice Item row, you have to mention Asset name and associated fixed asset account should be set as Expense Account. Fixed asset accounts are identified based on "Fixed Asset" account type.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset-purchase-invoice.png">

System will validate purchase date, supplier with the value mentioned in the Asset record. On submission of the Invoice, the "Fixed Asset Account" will be debited. It will also update Purchase Invoice number in the Asset.


## Sell an ssset

To sale an asset, create a Sales Invoice against the item linked with the asset. On submission of Sales Invoice, following entries will take place:

- "Receivable Account" (Debtors) will be debited by the sales amount.
- "Fixed Asset Account" will be credited by the purchase amount of asset.
- "Accumulated Depreciation Account" will be debited by the total depreciated amount till now.
- "Gain/Loss Account on Asset Disposal" will be credited/debited based on gain/loss amount. The Gain/Loss account can be set in Company record.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/asset-sales.png">


## Scrap an Asset

You can scrap an asset anytime using the "Scrap Asset" button in the Asset record. The "Gain/Loss Account on Asset Disposal" mentioned in the Company is debited by the Current Value (After Depreciation) of the asset. , After scrapping, you can also restore the asset using "Restore Asset" button.

<img class="screenshot" alt="Asset" src="{{docs_base_url}}/assets/img/accounts/scrap-journal-entry.png">