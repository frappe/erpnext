# Workflows
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Um es mehreren unterschiedlichen Personen zu erlauben viele verschiedene Anfragen zu übertragen, die dann von unterschiedlichen Benutzern genehmigt werden müssen, folgt ERPNext den Bedingungen eines Workflows. ERPNext protokolliert die unterschiedlichen Berechtigungen vor dem Übertragen mit.

Unten Sehen Sie ein Beispiel eines Worklflows.

Wenn ein Benutzer einen Urlaub beantragt, dann wird seine Anfrage an die Personalabteilung weiter geleitet. Die Personalabteilung, repräsentiert durch einen Mitarbeiter der Personalabteilung, wird diese Anfrage dann entweder genehmigen oder ablehnen. Wenn dieser Prozess abgeschlossen ist, dann bekommt der Vorgesetzte des Benutzers (der Urlaubsgenehmiger) eine Mitteilung, dass die Personalabteilung den Antrag genehmigt oder abgelehnt hat. Der Vorgesetzte, der die genehmigende Instanz ist, wird dann den Antrag entweder genehmigen oder ablehnen. Dementsprechend bekommt der Benutzer dann eine Genehmigung oder eine Ablehnung.

<img class="screenshot" alt="Workflow" src="/docs/assets/img/setup/workflow-leave-fl.jpg">

Um einen Workflow und Übergangsregeln zu erstellen, gehen Sie zu:

> Einstellungen > Workflow > Workflow > Neu

#### Schritt 1: Geben Sie die unterschiedlichen Zustände des Prozesses Urlaubsantrag ein.

<img class="screenshot" alt="Workflow" src="/docs/assets/img/setup/workflow-1.png">

#### Schritt 2: Geben Sie die Übergangsregeln ein.

<img class="screenshot" alt="Workflow" src="/docs/assets/img/setup/workflow-2.png">

Hinweise:

> Hinweis 1: Wenn Sie einen Workflow erstellen überschreiben Sie grundlegend den Kode, der für dieses Dokument erstellt wurde. Dementsprechend arbeitet das Dokument dann nach Ihrem Workflow und nicht mehr auf dem voreingestellten Kode. Deshalb gibt es wahrscheinlich keine Schaltfläche zum Übertragen, wenn Sie diese nicht im Workflow definiert haben.

> Hinweis 2: Der Dokumentenstatus für "Gespeichert" ist "0", für "Übertragen" "1" und für "Storniert" "2".

> Hinweis 3: Ein Dokument kann nicht storniert werden bis es übertragen wurde.

> Hinweis 4: Wenn Sie die Möglichkeit haben wollen zu stornieren, dann müssen Sie einen Workflow-Übergang erstellen, der Ihnen nach dem Übertragen das Stornieren anbietet.

#### Beispiel eines Urlaubsantrags-Prozesses

Gehen Sie in das Modul Personalwesen und klicken Sie auf Urlaubsantrag. Beantragen Sie einen Urlaub.

Wenn ein Urlaubsantrag übertragen wird, steht der Status in der Ecke der rechten Seite auf "Beantragt".

<img class="screenshot" alt="Workflow" src="/docs/assets/img/setup/workflow-3.png">

Wenn sich ein Mitarbeiter der Personalabteilung anmeldet, dann kann er den Antrag genehmigen oder ablehnen. Wenn eine Genehmigung erfolgt, wechselt der Status in der rechten Ecke zu "Genehmigt". Es wird jedoch ein blaues Informationssymbol angezeigt, welches aussagt, dass der Urlaubsantrag noch anhängig ist.

<img class="screenshot" alt="Workflow" src="/docs/assets/img/setup/workflow-4.png">

Wenn der Urlaubsgenehmiger die Seite mit den Urlaubsanträgen öffnet, kann er den Status von "Genehmigt" auf "Abgelehnt" ändern.

<img class="screenshot" alt="Workflow" src="/docs/assets/img/setup/workflow-5.png">

{next}
