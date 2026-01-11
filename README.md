# 🚌 Τηλεματική ΟΑΣΑ – Raspaberry People Count
Αυτό είναι το Project το οποίο θα γίνει Deploy σε ένα Raspberry PI το οποίο θα είναι τοποθετημένο στο λεωφορείο και θα κάνει καταμέτρηση των επιβατω΄ν αποστέλοντας αυτή την πληροφορία στον Application Server. 
## Βήματα εγκατάστασης του προγράμματος
1) Αφού γίνει Clone το Repository εκτελούμε
```
cd people_count_final
```
2) Παραμετροποιούμε - Ρυθμίζουμε σωστά το αρχείο .env
```
vi .env
```
3) Κάνουμε εγκατάσταση όλων των απαραίτητων βιβλιοθηκών - πακέτων
```
pip install -r requirements.txt
``` 
4) Εκτελούμε
```
sudo chmod +x start.sh
./start.sh
```
