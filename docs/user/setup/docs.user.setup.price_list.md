---
{
	"_label": "Price Lists"
}
---
A Price List is a place where different rate plans can be stored. It’s a name you give to a set of Item Prices stored under a particular Price List.

An Item can have multiple prices based on customer, currency, region, shipping cost etc, which can be stored as different rate plans. In ERPNext, you are required to store all the lists seperately. Buying Price List is different from Selling Price List and thus is stored separately. 

> Setup > Price List


![Price-List](img/price-lists.png)


> For multiple currencies, maintain multiple Price Lists.

<br>
### Add Item in Price List

> Setup > Item Price

- Enter Price List and Item Code, Valid for Buying or Selling, Item Name and Item Description will be automatically fetched.
- Enter Rate and save the document.

![Item-Price](img/item-price.png)

For bulk upload of Item Prices, use [Data Import Tool](docs.user.setup.data_import.html)