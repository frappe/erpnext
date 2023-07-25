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

# flake8: noqa: F401

from .albania import Albania, AL, ALB
from .algeria import Algeria, DZ, DZA
from .american_samoa import AmericanSamoa, AS, ASM, HolidaysAS
from .andorra import Andorra, AD, AND
from .angola import Angola, AO, AGO
from .argentina import Argentina, AR, ARG
from .armenia import Armenia, AM, ARM
from .aruba import Aruba, AW, ABW
from .australia import Australia, AU, AUS
from .austria import Austria, AT, AUT
from .azerbaijan import Azerbaijan, AZ, AZE
from .bahrain import Bahrain, BH, BAH
from .bangladesh import Bangladesh, BD, BGD
from .belarus import Belarus, BY, BLR
from .belgium import Belgium, BE, BEL
from .belize import Belize, BZ, BLZ
from .bolivia import Bolivia, BO, BOL
from .bosnia_and_herzegovina import BosniaAndHerzegovina, BA, BIH
from .botswana import Botswana, BW, BWA
from .brazil import Brazil, BR, BRA
from .brunei import Brunei, BN, BRN
from .bulgaria import Bulgaria, BG, BLG
from .burkina_faso import BurkinaFaso, BF, BFA
from .burundi import Burundi, BI, BDI
from .cambodia import Cambodia, KH, KHM
from .cameroon import Cameroon, CM, CMR
from .canada import Canada, CA, CAN
from .chad import Chad, TD, TCD
from .chile import Chile, CL, CHL
from .china import China, CN, CHN
from .colombia import Colombia, CO, COL
from .costa_rica import CostaRica, CR, CRI
from .croatia import Croatia, HR, HRV
from .cuba import Cuba, CU, CUB
from .curacao import Curacao, CW, CUW
from .cyprus import Cyprus, CY, CYP
from .czechia import Czechia, CZ, CZE
from .denmark import Denmark, DK, DNK
from .djibouti import Djibouti, DJ, DJI
from .dominican_republic import DominicanRepublic, DO, DOM
from .ecuador import Ecuador, EC, ECU
from .egypt import Egypt, EG, EGY
from .el_salvador import ElSalvador, SV, SLV
from .estonia import Estonia, EE, EST
from .eswatini import Eswatini, SZ, SZW, Swaziland
from .ethiopia import Ethiopia, ET, ETH
from .finland import Finland, FI, FIN
from .france import France, FR, FRA
from .gabon import Gabon, GA, GAB
from .georgia import Georgia, GE, GEO
from .germany import Germany, DE, DEU
from .greece import Greece, GR, GRC
from .guam import Guam, GU, GUM, HolidaysGU
from .guatemala import Guatemala, GT, GUA
from .honduras import Honduras, HN, HND
from .hongkong import HongKong, HK, HKG
from .hungary import Hungary, HU, HUN
from .iceland import Iceland, IS, ISL
from .india import India, IN, IND
from .indonesia import Indonesia, ID, IDN
from .ireland import Ireland, IE, IRL
from .isle_of_man import IsleOfMan, IM, IMN
from .israel import Israel, IL, ISR
from .italy import Italy, IT, ITA
from .jamaica import Jamaica, JM, JAM
from .japan import Japan, JP, JPN
from .kazakhstan import Kazakhstan, KZ, KAZ
from .kenya import Kenya, KE, KEN
from .kyrgyzstan import Kyrgyzstan, KG, KGZ
from .latvia import Latvia, LV, LVA
from .lesotho import Lesotho, LS, LSO
from .liechtenstein import Liechtenstein, LI, LIE
from .lithuania import Lithuania, LT, LTU
from .luxembourg import Luxembourg, LU, LUX
from .madagascar import Madagascar, MG, MDG
from .malawi import Malawi, MW, MWI
from .malaysia import Malaysia, MY, MYS
from .malta import Malta, MT, MLT
from .marshall_islands import MarshallIslands, MH, MHL, HolidaysMH
from .mexico import Mexico, MX, MEX
from .moldova import Moldova, MD, MDA
from .monaco import Monaco, MC, MCO
from .montenegro import Montenegro, ME, MNE
from .morocco import Morocco, MA, MOR
from .mozambique import Mozambique, MZ, MOZ
from .namibia import Namibia, NA, NAM
from .netherlands import Netherlands, NL, NLD
from .new_zealand import NewZealand, NZ, NZL
from .nicaragua import Nicaragua, NI, NIC
from .nigeria import Nigeria, NG, NGA
from .north_macedonia import NorthMacedonia, MK, MKD
from .northern_mariana_islands import NorthernMarianaIslands, MP, MNP, HolidaysMP
from .norway import Norway, NO, NOR
from .pakistan import Pakistan, PK, PAK
from .panama import Panama, PA, PAN
from .paraguay import Paraguay, PY, PRY
from .peru import Peru, PE, PER
from .philippines import Philippines, PH, PHL
from .poland import Poland, PL, POL
from .portugal import Portugal, PT, PRT
from .puerto_rico import PuertoRico, PR, PRI, HolidaysPR
from .romania import Romania, RO, ROU
from .russia import Russia, RU, RUS
from .san_marino import SanMarino, SM, SMR
from .saudi_arabia import SaudiArabia, SA, SAU
from .serbia import Serbia, RS, SRB
from .singapore import Singapore, SG, SGP
from .slovakia import Slovakia, SK, SVK
from .slovenia import Slovenia, SI, SVN
from .south_africa import SouthAfrica, ZA, ZAF
from .south_korea import SouthKorea, KR, KOR, Korea
from .spain import Spain, ES, ESP
from .sweden import Sweden, SE, SWE
from .switzerland import Switzerland, CH, CHE
from .taiwan import Taiwan, TW, TWN
from .thailand import Thailand, TH, THA
from .tunisia import Tunisia, TN, TUN
from .turkey import Turkey, TR, TUR
from .ukraine import Ukraine, UA, UKR
from .united_arab_emirates import UnitedArabEmirates, AE, ARE
from .united_kingdom import UnitedKingdom, GB, GBR, UK
from .united_states import UnitedStates, US, USA
from .united_states_minor_outlying_islands import (
    UnitedStatesMinorOutlyingIslands,
    UM,
    UMI,
    HolidaysUM,
)
from .united_states_virgin_islands import UnitedStatesVirginIslands, VI, VIR, HolidaysVI
from .uruguay import Uruguay, UY, URY
from .uzbekistan import Uzbekistan, UZ, UZB
from .vatican_city import VaticanCity, VA, VAT
from .venezuela import Venezuela, VE, VEN
from .vietnam import Vietnam, VN, VNM
from .zambia import Zambia, ZM, ZMB
from .zimbabwe import Zimbabwe, ZW, ZWE
