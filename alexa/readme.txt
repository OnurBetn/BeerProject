Accedere ad Amazon Developer con un qualsiasi account Amazon (link: https://developer.amazon.com/alexa/console/ask);

Cliccare su "Create Skill", inserire uno Skill name (es. IoTBeerBot), e impostare l'inglese come lingua;
lasciare tutto il resto invariato e cliccare su "Create skill";

Nella lista di sinistra andare su "JSON Editor" (utima voce di Interaction Model) e caricare il file interaction_model.json;
Cliccare su Save Model (barra in alto) e poi Build Model.

Scaricare ngrok (link: https://ngrok.com/download), estrarre il file .exe, fare doppio click su di esso 
e digitare sul terminale "ngrok.exe http 5000".
Tornare su Amazon Developer e nella lista di sinistra andare su Endpoint, selezionare HTTPS e 
in Default Region digitare l'indirizzo assegnatoci da ngrok alla seconda voce Forwarding (https://xxxxxxxx.ngrok.io), 
in SSL certificate selezionare la seconda opzione. Salvare l'endpoint (barra in alto).
*** L'endpoint dovrà essere aggiornato in Amazon Developer ogni volta che si riavvia ngrok
poichè la versione free ci assegna un indirizzo diverso ad ogni avvio. ***

Aprire il file data.py, inserire lo Skill ID e l'indirizzo del catalog. 
Lo Skill ID si trova cliccando su Your Skills (in alto a sinistra) nella Amazon
Developer Console e poi su View Skill ID sotto il nome della skill nella lista.

Installare le librerie necessarie (pip install ask-sdk, flask-ask-sdk, num2words).
Runnare il file alexa_bot.py; la skill può essere testata o dalla sezione Test sulla Amazon Developer Console o 
scaricando l'app Amazon Alexa su smartphone e accendendo con lo stesso account utilizzato in Amazon Developer.

Per invocare la skill, dire "Alexa, start/open/run Beer bot".
Dopodiché si possono chiedere informazioni come:
"Which devices are connected?"
"Which devices are connected in {Process}?"

"What is the {Resource} measured by {DeviceID}?"
"Get current {Resource} in {DeviceID}"

"What are the {Resource} thresholds of {DeviceID}?"

"How long until {Resource} threshold is reached in {DeviceID}"
