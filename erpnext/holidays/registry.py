#  python-holidays
#  ---------------
#  A fast, efficient Python library for generating country, province and state
#  specific sets of holidays on the fly. It aims to make determining whether a
#  specific date is a holiday as fast and flexible as possible.
#
#  Authors: dr-prodigy <dr.prodigy.github@gmail.com> (c) 2017-2023
#           ryanss <ryanssdev@icloud.com> (c) 2014-2017
#  Website: https://github.com/dr-prodigy/python-holidays
#  License: MIT (see LICENSE file)

import importlib
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from holidays.holiday_base import HolidayBase

RegistryDict = Dict[str, Tuple[str, ...]]

COUNTRIES: RegistryDict = {
    "albania": ("Albania", "AL", "ALB"),
    "algeria": ("Algeria", "DZ", "DZA"),
    "american_samoa": ("AmericanSamoa", "AS", "ASM", "HolidaysAS"),
    "andorra": ("Andorra", "AD", "AND"),
    "angola": ("Angola", "AO", "AGO"),
    "argentina": ("Argentina", "AR", "ARG"),
    "armenia": ("Armenia", "AM", "ARM"),
    "aruba": ("Aruba", "AW", "ABW"),
    "australia": ("Australia", "AU", "AUS"),
    "austria": ("Austria", "AT", "AUT"),
    "azerbaijan": ("Azerbaijan", "AZ", "AZE"),
    "bahrain": ("Bahrain", "BH", "BAH"),
    "bangladesh": ("Bangladesh", "BD", "BGD"),
    "belarus": ("Belarus", "BY", "BLR"),
    "belgium": ("Belgium", "BE", "BEL"),
    "belize": ("Belize", "BZ", "BLZ"),
    "bolivia": ("Bolivia", "BO", "BOL"),
    "bosnia_and_herzegovina": ("BosniaAndHerzegovina", "BA", "BIH"),
    "botswana": ("Botswana", "BW", "BWA"),
    "brazil": ("Brazil", "BR", "BRA"),
    "brunei": ("Brunei", "BN", "BRN"),
    "bulgaria": ("Bulgaria", "BG", "BLG"),
    "burkina_faso": ("BurkinaFaso", "BF", "BFA"),
    "burundi": ("Burundi", "BI", "BDI"),
    "cambodia": ("Cambodia", "KH", "KHM"),
    "cameroon": ("Cameroon", "CM", "CMR"),
    "canada": ("Canada", "CA", "CAN"),
    "chad": ("Chad", "TD", "TCD"),
    "chile": ("Chile", "CL", "CHL"),
    "china": ("China", "CN", "CHN"),
    "colombia": ("Colombia", "CO", "COL"),
    "costa_rica": ("CostaRica", "CR", "CRI"),
    "croatia": ("Croatia", "HR", "HRV"),
    "cuba": ("Cuba", "CU", "CUB"),
    "curacao": ("Curacao", "CW", "CUW"),
    "cyprus": ("Cyprus", "CY", "CYP"),
    "czechia": ("Czechia", "CZ", "CZE"),
    "denmark": ("Denmark", "DK", "DNK"),
    "djibouti": ("Djibouti", "DJ", "DJI"),
    "dominican_republic": ("DominicanRepublic", "DO", "DOM"),
    "ecuador": ("Ecuador", "EC", "ECU"),
    "egypt": ("Egypt", "EG", "EGY"),
    "el_salvador": ("ElSalvador", "SV", "SLV"),
    "estonia": ("Estonia", "EE", "EST"),
    "eswatini": ("Eswatini", "SZ", "SZW", "Swaziland"),
    "ethiopia": ("Ethiopia", "ET", "ETH"),
    "finland": ("Finland", "FI", "FIN"),
    "france": ("France", "FR", "FRA"),
    "gabon": ("Gabon", "GA", "GAB"),
    "georgia": ("Georgia", "GE", "GEO"),
    "germany": ("Germany", "DE", "DEU"),
    "greece": ("Greece", "GR", "GRC"),
    "guam": ("Guam", "GU", "GUM", "HolidaysGU"),
    "guatemala": ("Guatemala", "GT", "GUA"),
    "honduras": ("Honduras", "HN", "HND"),
    "hongkong": ("HongKong", "HK", "HKG"),
    "hungary": ("Hungary", "HU", "HUN"),
    "iceland": ("Iceland", "IS", "ISL"),
    "india": ("India", "IN", "IND"),
    "indonesia": ("Indonesia", "ID", "IDN"),
    "ireland": ("Ireland", "IE", "IRL"),
    "isle_of_man": ("IsleOfMan", "IM", "IMN"),
    "israel": ("Israel", "IL", "ISR"),
    "italy": ("Italy", "IT", "ITA"),
    "jamaica": ("Jamaica", "JM", "JAM"),
    "japan": ("Japan", "JP", "JPN"),
    "kazakhstan": ("Kazakhstan", "KZ", "KAZ"),
    "kenya": ("Kenya", "KE", "KEN"),
    "kyrgyzstan": ("Kyrgyzstan", "KG", "KGZ"),
    "latvia": ("Latvia", "LV", "LVA"),
    "lesotho": ("Lesotho", "LS", "LSO"),
    "liechtenstein": ("Liechtenstein", "LI", "LIE"),
    "lithuania": ("Lithuania", "LT", "LTU"),
    "luxembourg": ("Luxembourg", "LU", "LUX"),
    "madagascar": ("Madagascar", "MG", "MDG"),
    "malawi": ("Malawi", "MW", "MWI"),
    "malaysia": ("Malaysia", "MY", "MYS"),
    "malta": ("Malta", "MT", "MLT"),
    "marshall_islands": ("MarshallIslands", "MH", "MHL", "HolidaysMH"),
    "mexico": ("Mexico", "MX", "MEX"),
    "moldova": ("Moldova", "MD", "MDA"),
    "monaco": ("Monaco", "MC", "MCO"),
    "montenegro": ("Montenegro", "ME", "MNE"),
    "morocco": ("Morocco", "MA", "MOR"),
    "mozambique": ("Mozambique", "MZ", "MOZ"),
    "namibia": ("Namibia", "NA", "NAM"),
    "netherlands": ("Netherlands", "NL", "NLD"),
    "new_zealand": ("NewZealand", "NZ", "NZL"),
    "nicaragua": ("Nicaragua", "NI", "NIC"),
    "nigeria": ("Nigeria", "NG", "NGA"),
    "north_macedonia": ("NorthMacedonia", "MK", "MKD"),
    "northern_mariana_islands": ("NorthernMarianaIslands", "MP", "MNP", "HolidaysMP"),
    "norway": ("Norway", "NO", "NOR"),
    "pakistan": ("Pakistan", "PK", "PAK"),
    "panama": ("Panama", "PA", "PAN"),
    "paraguay": ("Paraguay", "PY", "PRY"),
    "peru": ("Peru", "PE", "PER"),
    "philippines": ("Philippines", "PH", "PHL"),
    "poland": ("Poland", "PL", "POL"),
    "portugal": ("Portugal", "PT", "PRT"),
    "puerto_rico": ("PuertoRico", "PR", "PRI", "HolidaysPR"),
    "romania": ("Romania", "RO", "ROU"),
    "russia": ("Russia", "RU", "RUS"),
    "san_marino": ("SanMarino", "SM", "SMR"),
    "saudi_arabia": ("SaudiArabia", "SA", "SAU"),
    "serbia": ("Serbia", "RS", "SRB"),
    "singapore": ("Singapore", "SG", "SGP"),
    "slovakia": ("Slovakia", "SK", "SVK"),
    "slovenia": ("Slovenia", "SI", "SVN"),
    "south_africa": ("SouthAfrica", "ZA", "ZAF"),
    "south_korea": ("SouthKorea", "KR", "KOR", "Korea"),
    "spain": ("Spain", "ES", "ESP"),
    "sweden": ("Sweden", "SE", "SWE"),
    "switzerland": ("Switzerland", "CH", "CHE"),
    "taiwan": ("Taiwan", "TW", "TWN"),
    "thailand": ("Thailand", "TH", "THA"),
    "tunisia": ("Tunisia", "TN", "TUN"),
    "turkey": ("Turkey", "TR", "TUR"),
    "ukraine": ("Ukraine", "UA", "UKR"),
    "united_arab_emirates": ("UnitedArabEmirates", "AE", "ARE"),
    "united_kingdom": ("UnitedKingdom", "GB", "GBR", "UK"),
    "united_states_minor_outlying_islands": (
        "UnitedStatesMinorOutlyingIslands",
        "UM",
        "UMI",
        "HolidaysUM",
    ),
    "united_states_virgin_islands": ("UnitedStatesVirginIslands", "VI", "VIR", "HolidaysVI"),
    "united_states": ("UnitedStates", "US", "USA"),
    "uruguay": ("Uruguay", "UY", "URY"),
    "uzbekistan": ("Uzbekistan", "UZ", "UZB"),
    "vatican_city": ("VaticanCity", "VA", "VAT"),
    "venezuela": ("Venezuela", "VE", "VEN"),
    "vietnam": ("Vietnam", "VN", "VNM"),
    "zambia": ("Zambia", "ZM", "ZMB"),
    "zimbabwe": ("Zimbabwe", "ZW", "ZWE"),
}

FINANCIAL: RegistryDict = {
    "european_central_bank": ("EuropeanCentralBank", "ECB", "TAR"),
    "ny_stock_exchange": ("NewYorkStockExchange", "NYSE", "XNYS"),
}


class EntityLoader:
    """Country and financial holidays entities lazy loader."""

    __slots__ = ("entity", "entity_name", "module_name")

    def __init__(self, path: str, *args, **kwargs) -> None:
        """Set up a lazy loader."""
        if args:
            raise TypeError(
                "This is a python-holidays entity loader class. "
                "For entity inheritance purposes please import a class you "
                "want to derive from directly: e.g., "
                "`from holidays.countries import Entity` or "
                "`from holidays.financial import Entity`."
            )

        entity_path = path.split(".")

        self.entity = None
        self.entity_name = entity_path[-1]
        self.module_name = ".".join(entity_path[0:-1])

        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs) -> HolidayBase:
        """Create a new instance of a lazy-loaded entity."""
        cls = self.get_entity()
        return cls(*args, **kwargs)  # type: ignore[misc, operator]

    def __getattr__(self, name: str) -> Optional[Any]:
        """Return attribute of a lazy-loaded entity."""
        cls = self.get_entity()
        return getattr(cls, name)

    def __str__(self) -> str:
        """Return lazy loader object string representation."""
        return (
            f"A lazy loader for {self.get_entity()}. For inheritance please "
            f"use the '{self.module_name}.{self.entity_name}' class directly."
        )

    def get_entity(self) -> Optional[HolidayBase]:
        """Return lazy-loaded entity."""
        if self.entity is None:
            self.entity = getattr(importlib.import_module(self.module_name), self.entity_name)

        return self.entity

    @staticmethod
    def _get_entity_codes(
        container: RegistryDict,
        entity_length: Union[int, Iterable[int]],
        include_aliases: bool = True,
    ) -> Iterable[str]:
        entity_length = {entity_length} if isinstance(entity_length, int) else set(entity_length)
        for entities in container.values():
            for entity in entities:
                if len(entity) in entity_length:
                    yield entity
                    # Assuming that the alpha-2 code goes first.
                    if not include_aliases:
                        break

    @staticmethod
    def get_country_codes(include_aliases: bool = True) -> Iterable[str]:
        """Get supported country codes.

        :param include_aliases:
            Whether to include entity aliases (e.g. UK for GB).
        """
        return EntityLoader._get_entity_codes(COUNTRIES, 2, include_aliases)

    @staticmethod
    def get_financial_codes(include_aliases: bool = True) -> Iterable[str]:
        """Get supported financial codes.

        :param include_aliases:
            Whether to include entity aliases(e.g. TAR for ECB, XNYS for NYSE).
        """
        return EntityLoader._get_entity_codes(FINANCIAL, (3, 4), include_aliases)

    @staticmethod
    def load(prefix: str, scope: Dict) -> None:
        """Load country or financial entities."""
        entity_mapping = COUNTRIES if prefix == "countries" else FINANCIAL
        for module, entities in entity_mapping.items():
            scope.update(
                {
                    entity: EntityLoader(f"holidays.{prefix}.{module}.{entity}")
                    for entity in entities
                }
            )
