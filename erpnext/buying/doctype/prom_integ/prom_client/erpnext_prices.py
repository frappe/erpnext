from frappeclient import FrappeClient as Client
import pandas as pd


class ERPNext:
    """
    This class is used to get the item prices from the ERPNext instance
    also it can be used to transform the data to the dataframe
    and save it to the csv or excel file
    """

    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.client = Client(url)
        self.client.login(username, password)
        self.items = self.get_items()
        self.item_prices = self.get_item_prices()

    def save_to_csv(self, filename):
        """
        Save dataframe to csv
        Args:
            filename (str): filename
        """
        self.df.to_csv(filename, index=False)

    def save_to_excel(self, filename):
        """
        Save dataframe to excel
        Args:
            filename (str): filename
        """
        self.df.to_excel(filename, index=False)

    def get_items(self):
        """
        This method is used to get the items from the ERPNext instance
        :return: list of items
        """
        return self.client.get_list("Website Item")

    def get_item(self, item_code):
        """
        This method is used to get the item from the ERPNext instance
        :param item_code:
        :return:
        """
        return self.client.get_doc("Website Item", item_code)

    def get_item_price(self, item_code):
        '''
        Get item price
        :param item_code:
        :return:
        '''
        return self.client.get_doc("Item Price", item_code)

    def get_item_prices(self):
        '''
        Get item prices
        :return:
        '''
        return self.client.get_list("Item Price")

    def get_item_price_by_item_code(self, item_code):
        '''
        Get item price by item code
        :param item_code:
        :return:
        '''
        return self.client.get_list("Item Price", filters={"item_code": item_code})

    def get_item_price_by_item_group(self, item_group):
        '''
        Get item price by item group
        :param item_group:
        :return:
        '''
        return self.client.get_list("Item Price", filters={"item_group": item_group})

    def get_item_price_by_price_list(self, price_list):
        """
        Get item price by price list
        :param price_list:
        :return:
        """
        return self.client.get_list("Item Price", filters={"price_list": price_list})

    def get_item_price_by_item_code_and_price_list(self, item_code, price_list):
        """
        Get item price by item code and price list
        :param item_code:
        :param price_list:
        :return:
        """
        return self.client.get_list(
            "Item Price", filters={"item_code": item_code, "price_list": price_list}
        )

    def get_doctype_list(self, doctype, filters, fields):
        """
        Get doctype list
        Args:
            doctype (str): doctype name
            filters (dict): filters
            fields (list): fields to return
        Returns:
            list: list of documents

        """
        return self.client.get_list(  #
            doctype,
            fields=fields,
            limit_page_length=5000,
            filters=filters,
        )

    def get_doctype(self, doctype, name, fields):
        """
        Get doctype
        Args:
            doctype (str): doctype name
            name (str): name of the document
            fields (list): fields to return
        Returns:
            dict: document

        """
        return self.client.get_doc(doctype, name, fields=fields)

    def get_item_price_list(self, website_item_codes):
        """
        Get item price list
        Args:
            website_item_codes (list): list of website item codes
        Returns:
            list: list of item prices
        """
        items = []  # list of items
        for item_code in website_item_codes:  # iterate over website item codes
            item_prices = self.get_item_price(item_code)  # get item price
            if item_prices:  # if item price exists
                items.append(
                    {"item_code": item_code, "item_prices": item_prices}
                )  # add item to list
        return items

    def get_item_serch_terms_ukr(self, item_code):
        """
        Get item search terms ukr
        Args:
            item_code (str): item code
        Returns:
            list: list of search terms
        """
        item = self.get_item(item_code)
        search_terms = []
        if item.get("serch_terms_ukr"):
            search_terms = item.get("products_on_erp").split(",")
        return search_terms

    def items_price_list_to_df(self):
        """
        Convert item price list to dataframe
        Returns:
            dataframe: dataframe with item prices
        """
        df = pd.DataFrame.from_dict(self.items).explode("item_prices")  # explode item_prices
        df = df.assign(
            **df["item_prices"].apply(pd.Series)
        )  # split item_prices to columns
        df = df.drop(columns=["item_prices"])  # drop item_prices column
        return df

