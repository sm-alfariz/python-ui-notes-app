# python-ui-notes-app
![Alt text](screen-shoots/sc-01.png "Optional Title Text")
![Alt text](screen-shoots/sc-02.png "Optional Title Text")

this app use sqlite3 as database for easy to stand alone app

## how to run

make sure you have python 3.13 or higher and create virtual environment and install requirements with `pip install -r requirements.txt`

then run the app with `python -m main`

## features

1. create note show window dialog for new notes
2. read note show list of notes in table
3. update note show window dialog for update notes
4. delete note show window dialog for delete notes
5. search note show list of notes in table with search input
6. detail note with double click at current row show window dialog

## pyinstaller

if you want to make it standalone app you can use pyinstaller
make sure you have pyinstaller installed with `pip install pyinstaller`
then run the app with `pyinstaller --onefile main.py` im use arch linux and build standalone for linux with `pyinstaller --onefile --windowed main.py` if you use windows you can use `pyinstaller --onefile --windowed main.py` and run itu on your windows machine see pyinstaller doc for more info https://pyinstaller.readthedocs.io/en/stable/ and https://pyinstaller.readthedocs.io/en/stable/usage.html for more info about pyinstaller usage  