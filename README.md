# EnHb

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-Supported-0078D6?logo=windows&logoColor=white)
![Keyboard Hotkeys](https://img.shields.io/badge/Hotkeys-Ctrl%2BShift%2BH%20%7C%20Ctrl%2BShift%2BE-purple)
![Language](https://img.shields.io/badge/Language-Hebrew%20%26%20English-green)
![Open Source](https://img.shields.io/badge/Open%20Source-Yes-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

**כתבת הכל באנגלית אבל התכוונת לכתוב בעברית?**  
תשתמש ב**EnHb** בשביל להפוך טקסט אנגלי לטקסט עברי הפוך ומתוקן וגם להפך!

EnHb היא תוכנה פשוטה ומהירה שממירה טקסט שנכתב בטעות בשפה הלא נכונה לפי פריסת המקלדת.
לדוגמה, אם כתבת טקסט בעברית כשהמקלדת הייתה על אנגלית, EnHb תתקן את זה בלחיצת קיצור.

## מה EnHb עושה?

- ממירה טקסט בעברית לטקסט אנגלי
- עובדת עם קיצורי מקשים

## קיצורי מקשים

| פעולה | קיצור |
|---|---|
| המרה מאנגלית לעברית | `Ctrl + Shift + H` |
| המרה מעברית לאנגלית | `Ctrl + Shift + E` |

## איך זה עובד?

EnHb קוראת את הטקסט שנבחר, ממירה כל תו לפי מיקום המקש במקלדת, ומדביקה בחזרה את הטקסט המתוקן.

לדוגמה:

```text
akuo
````

יהפוך ל:

```text
שלום
```

## שימושים אפשריים

* תיקון טקסט שנכתב בטעות באנגלית במקום בעברית
* תיקון טקסט עברי שנכתב בטעות כשהמקלדת הייתה באנגלית
* חיסכון בזמן במקום למחוק ולכתוב מחדש

## התקנה והרצה

1. התקן Python
2. התקן את הספריות הדרושות:

```bash
pip install keyboard clipboard pyautogui
```

3. הרץ את הקובץ:

```bash
python main.py
```

## דרישות

* Windows
* Python
* הרשאות מתאימות לקיצורי מקשים גלובליים

## הערות

בחלק מהמחשבים ייתכן שיהיה צורך להריץ את התוכנה כמנהל מערכת כדי שקיצורי המקשים יעבדו בכל מקום.
