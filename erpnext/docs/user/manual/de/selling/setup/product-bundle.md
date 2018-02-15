# Produkt-Bundle
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Der Begriff "Produkt-Bundle" ist gleichbedeutend mit der Stückliste des Vertriebs. Es handelt sich dabei um eine Vorlage, in der Sie Artikel zusammenstellen können, die zusammengepackt werden und als ein Artikel verkauft werden. Beispiel: Wenn ein Laptop geliefert wird, müssen Sie sicher stellen, dass das Ladekabel, die Maus und die Tragetasche mitgeliefert werden und der Lagerbestand dieser Artikel dementsprechend bearbeitet wird. Um dieses Szenario abzubilden, können Sie für den Hauptartikel, z. B. den Laptop, die Option "Produkt-Bundle"einstellen, und die zu liefernden Artikel wie Laptop + Ladekabel + anderes Zubehör als Unterartikel auflisten.

Im Folgenden sind die Schritte dargestellt, wie die Vorlage zum Produkt-Bundle eingestellt wird, und wie sie in Vertriebsaktionen genutzt wird.

### Ein neues Produkt-Bundle erstellen

Um ein neues Produkt-Bundle zu erstellen, gehen Sie zu:

> Vertrieb > Einstellungen > Produkt-Bundle > Neu

<img class="screenshot" alt="Produkt-Bundle" src="{{docs_base_url}}/assets/img/selling/product-bundle.png">

### Hauptartikel auswählen

In der Vorlage des Produkt-Bundles gibt es zwei Abschnitte. Produkt-Bundle-Artikel (Hauptartikel) und Paketartikel.

Für den Produkt-Bundle-Artikel wählen sie einen übergeordneten Artikel aus. Der übergeordnete Artikel darf **kein Lagerartikel** sein, da nicht er über das Lager verwaltet wird, sondern nur die Paketartikel. Wenn Sie den übergeordneten Artikel im Lager verwalten wollen, dann müssen Sie eine reguläre Stückliste erstellen und ihn über eine Lagertransaktion zusammen packen lassen.

### Unterartikel auswählen

Im Abschnitt Paketartikel listen Sie alle Unterartikel auf, die über das Lager verwaltet werden und an den Kunden geliefert werden.

### Produkt-Bundle in Vertriebstransaktionen

Wenn Vertriebstransaktionen erstellt werden, wie z. B. Ausgangsrechnung, Kundenauftrag und Lieferschein, dann wird der übergeordnete Artikel aus der Hauptartikelliste ausgewählt.

<img class="screenshot" alt="Produkt-Bundle" src="{{docs_base_url}}/assets/img/selling/product-bundle.gif">

Beim Auswählen des übergeordneten Artikels aus der Hauptartikelliste werden die Unterartikel aus der Tabelle "Packliste" der Transaktion angezogen. Wenn der Unterartikel ein serialisierter Artikel ist, können Sie seine Seriennummer direkt in der Packlistentabelle angeben. Wenn die Transaktion versendet wird, reduziert das System den Lagerbestand der Unterartikel auf dem Lager der in der Packlistentabelle angegeben ist.

####Produkt-Bundles nutzen um Angebote abzubilden

Diese Einsatzmöglichkeit von Produkt-Bundles wurde entdeckt, als ein Kunde, der mit Nahrungsmitteln handelte, nach einer Funktion fragte, Angebote wie "Kaufe eins und bekomme eines frei dazu" abzubilden. Um das umzusetzen, legte er einen Nicht-Lager-Artikel an, der als übergeordneter Artikel verwendet wurde. In der Beschreibung des Artikels gab er die Einzelheiten zu diesem Angebot und ein Bild an. Der Verkaufsartikel wurde dann als Packartikel ausgewählt, wobei die Menge 2 war. Somit zog das System immer dann, wenn ein Artikel über dieses Angebot verkauft wurde, eine Menge von 2 im Lager ab.

{next}
