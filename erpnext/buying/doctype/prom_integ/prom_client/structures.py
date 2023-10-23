webitem_fields = [
    'web_item_name',
    'name',
    'item_code',
    'description',
    'brand',
    'item_group',
    'website_image',
    'stock_uom',
    'weight_per_unit',
    'availability',
    'county_of_origin',
    'discount',
    'search_terms',
    'minimal_purchase_volume',
    'translation.specific_name',
    'translation.specific_description',
    'translation.search_requests',
    'selling_type',
    'marketplace_category.external_id'
]

prom_translate = {
    'specific_name': 'Назва_позиції',
    'web_item_name': 'Назва_позиції_укр',
    'name': 'Ідентифікатор_товару',
    'description': 'Опис_укр',
    'specific_description': 'Опис',
    'brand': 'Виробник',
    'item_group': 'Номер_групи',
    'website_image': 'Посилання_зображення',
    'stock_uom': 'Одиниця_виміру',
    'weight_per_unit': 'Вага,кг',
    'availability': 'Наявність',
    'county_of_origin': 'Країна_виробник',
    'discount': 'Знижка',
    'search_terms': 'Пошукові_запити_укр',
    'search_requests': 'Пошукові_запити',
    'minimal_purchase_volume': 'Мінімальний_обсяг_замовлення',
    'item_code': 'Код_товару',
    'price_list_rate': 'Ціна',
    'currency': 'Валюта',
    'value': 'Значение',
    'selling_type': 'Тип_товару',
    'external_id': 'Ідентифікатор_підрозділу'
}

webitem_uom = {
    'шт.': 'Unit',
    'м.': 'Meter',
    'кг.': 'Kg',
    'гр.': 'Gram',
    'кг': 'Kg',
    '': 'Unit',
    'ед.': 'Unit',
    'л': 'Litre'
}

stock_uom = {
    'Unit': 'шт.',
    'Meter': 'м',
    'Kg': 'кг',
    'Gram': 'г',
    'Litre': 'л'
}

prom_presence = {
    'available': '+',
    'not_available': '-',
    'order': "3", # int value required
    'service': '@',
    'waiting': '&'
}
erp_prom_availability = {
    'Є в наявності': '+',
    'Немає в наявності': '-',
    'Очікується': '&',
    'Послуга': '@',
    'Наявність на складі': '!'
    }