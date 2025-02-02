## LC-Anki

When practicing LeetCode, you often encounter similar questions but forget how to solve them. [Anki](https://apps.ankiweb.net/) is a full-platform memory tool based on the forgetting curve, supporting Mac, Linux, Windows, iOS and Android platforms. Anki is an excellent memory tool, but it requires manual card making, which is a very tedious and time-consuming process.

> Invest some time to automate or simplify a process to save more time in the future

**This project aims to capture the questions in LeetCode and automatically generate Anki decks to help with memorization.**

The captured data includes：

1. Question title, difficulty, description.
2. Official solution (Premium solutions require subscription to download).
3. Submission code of user AC.

## DEMO

|           Front            |           Back           |
| :------------------------: | :----------------------: |
| ![front](./demo/front.JPG) | ![back](./demo/back.JPG) |

[Sample Deck](https://github.com/varun-kanna/LeetCode-Anki/blob/master/data/LeetCode.apkg?raw=true)

## Instructions

First, clone the repository and install Python dependencies in a venv.

```bash
git clone https://github.com/Peng-YM/LeetCode-Anki.git
cd LeetCode-Anki
python -m venv venv
./venv/Scripts/Activate.ps1
pip3 install -r requirements.txt
```

Run the crawler and output the Anki deck to `./data/LeetCode.apkg` (as specified by `project.conf`).

```bash
python3 main.py
```

You need to obtain cookies for the first run. Running `main.py` will open a Chrome window. You can manually fill in the username and password to log in once.

> ⚠️ Notice:
>
> 1. If you need to log in again with the browser, just delete the `cookie.dat` in the directory.
> 2. If the browser driver is out of date (currently V86.0), go to Download [Selenium](<(https://chromedriver.chromium.org/downloads)>) Driver for Chrome and replace the old `vendor` driver.

Have fun using Anki to review the questions you have done.

## Customizing

If you don't like the default generated Anki card style, you can modify the following three parameters in `project.conf` to customize the generated Anki cards.

```properties
[DB]
path = ./data
debug = False

[Anki]
front = ./templates/front-side.html
back = ./templates/back-side.html
css = ./templates/style.css
output = ./data/LeetCode.apkg
```

-   `front`: the format of the front of the card
-   `back`: the format of the back of the card
-   `css`: the CSS style of the card

## LICENSE

This project is based on the GPL V3 open source agreement.

## Acknowledgements

This project is based on many excellent open source projects:

-   [genanki: A Library for Generating Anki Decks](https://github.com/kerrickstaley/genanki)

-   [Python Markdown: Python implementation of John Gruber's Markdown](https://github.com/Python-Markdown/markdown)
