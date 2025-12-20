import json
from pathlib import Path

syscohada_countries = [
	"bj",  # Bénin
	"bf",  # Burkina-Faso
	"cm",  # Cameroun
	"cf",  # Centrafrique
	"ci",  # Côte d'Ivoire
	"cg",  # Congo
	"km",  # Comores
	"ga",  # Gabon
	"gn",  # Guinée
	"gw",  # Guinée-Bissau
	"gq",  # Guinée Equatoriale
	"ml",  # Mali
	"ne",  # Niger
	"cd",  # République Démocratique du Congo
	"sn",  # Sénégal
	"td",  # Tchad
	"tg",  # Togo
]

folder = Path(__file__).parent
generic_charts = Path(folder).glob("syscohada*.json")

for file in generic_charts:
	with open(file) as f:
		chart = json.load(f)
	for country in syscohada_countries:
		chart["country_code"] = country
		json_object = json.dumps(chart, indent=4)
		with open(Path(folder, file.name.replace("syscohada", country)), "w") as outfile:
			outfile.write(json_object)
