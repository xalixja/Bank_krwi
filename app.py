from flask import Flask, render_template, request, redirect, session
from db.connection import get_db
from functools import wraps

app = Flask(__name__)
app.secret_key = "koko"   # zmień na swój

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # brak sesji → przekierowanie na login
            if "user_id" not in session:
                return redirect("/login")

            # jeśli podano wymaganą rolę → sprawdzamy
            if role and session.get("rola") != role:
                return redirect("/login")

            return f(*args, **kwargs)
        return wrapper
    return decorator
@app.route("/")
def index():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        login = request.form["login"]
        haslo = request.form["haslo"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
                    SELECT id_uzytkownika, rola
                    FROM Uzytkownicy
                    WHERE login = %s
                      AND haslo = public.crypt(%s, haslo)
                    """, (login, haslo))

        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["rola"] = user[1]

            return redirect("/welcome")

        else:
            error = "Niepoprawny login lub hasło"

    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        login = request.form["login"]
        haslo = request.form["haslo"]
        imie = request.form["imie"]
        nazwisko = request.form["nazwisko"]
        pesel = request.form["pesel"]
        grupa = request.form["grupa"]
        rh = request.form["rh"]
        kontakt = request.form["kontakt"]

        conn = get_db()
        cur = conn.cursor()

        #dodanie użytkownika
        cur.execute("""
                    INSERT INTO uzytkownicy (login, haslo, rola, data_rejestracji)
                    VALUES (%s, public.crypt(%s, public.gen_salt('bf')), 'DAWCA', CURRENT_DATE)
                        RETURNING id_uzytkownika;
                    """, (login, haslo))

        id_uzytkownika = cur.fetchone()[0]

        #dodanie dawcy
        cur.execute("""
                    INSERT INTO dawcy (imie, nazwisko, pesel, grupa_krwi, rh, kontakt, id_uzytkownika)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (imie, nazwisko, pesel, grupa, rh, kontakt, id_uzytkownika))

        conn.commit()
        cur.close()
        conn.close()

        #automatyczne logowanie po rejestracji
        session["user_id"] = id_uzytkownika
        session["rola"] = "DAWCA"

        return redirect("/welcome")

    return render_template("register.html", error=error)


@app.route("/welcome")
@login_required()
def welcome():
    rola = session.get("rola")
    return render_template("welcome.html", rola=rola)

@app.route("/dawca")
@login_required(role="DAWCA")
def panel_dawcy():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
                SELECT
                    d.imie,
                    d.nazwisko,
                    d.grupa_krwi,
                    d.rh,
                    COUNT(o.id_oddania) AS liczba_oddan,
                    (
                        SELECT z.status
                        FROM zgloszenia z
                        WHERE z.id_dawcy = d.id_dawcy
                          AND z.data_zgloszenia >= CURRENT_DATE
                        ORDER BY z.data_zgloszenia ASC
                        LIMIT 1
                    ) AS najblizsze_zgloszenie,
                    d.id_dawcy
                FROM dawcy d
                    LEFT JOIN oddania_krwi o ON o.id_dawcy = d.id_dawcy
                WHERE d.id_uzytkownika = %s
                GROUP BY d.id_dawcy, d.imie, d.nazwisko, d.grupa_krwi, d.rh;
                """, (user_id,))

    dane = cur.fetchone()

    id_dawcy = dane[6]

    # suma ml z widoku
    cur.execute("""
                SELECT suma_ml
                FROM widok_suma_ml
                WHERE id_dawcy = %s;
                """, (id_dawcy,))
    suma = cur.fetchone()
    suma_ml = suma[0] if suma else None

    # Daty oddań z widoku
    cur.execute("""
                SELECT pierwsze_oddanie, ostatnie_oddanie
                FROM widok_dat_oddan
                WHERE id_dawcy = %s;
                """, (id_dawcy,))
    daty = cur.fetchone()
    pierwsze = daty[0] if daty else None
    ostatnie = daty[1] if daty else None

    # Historia badań z widoku
    cur.execute("""
            SELECT data_badania, rodzaj_badania, wynik
            FROM widok_historia_badania
            WHERE dawca = %s
            ORDER BY data_badania DESC;
            """, (f"{dane[0]} {dane[1]}",))

    historia_badan = cur.fetchall()


    cur.close()
    conn.close()

    return render_template(
        "panel_dawcy.html",
        imie=dane[0],
        nazwisko=dane[1],
        grupa=dane[2],
        rh=dane[3],
        liczba_oddan=dane[4],
        najblizsze=dane[5],
        suma_ml=suma_ml,
        pierwsze=pierwsze,
        ostatnie=ostatnie,
        historia_badan=historia_badan
    )

@app.route("/dawca/dane")
@login_required(role="DAWCA")
def dane_dawcy():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
                SELECT imie, nazwisko, pesel, grupa_krwi, rh, kontakt
                FROM dawcy
                WHERE id_uzytkownika = %s;
                """, (user_id,))

    dane = cur.fetchone()
    cur.close()
    conn.close()

    return render_template(
        "dane_dawcy.html",
        imie=dane[0],
        nazwisko=dane[1],
        pesel=dane[2],
        grupa=dane[3],
        rh=dane[4],
        kontakt=dane[5]
    )

@app.route("/dawca/dane/edytuj", methods=["GET", "POST"])
@login_required(role="DAWCA")
def edytuj_dane_dawcy():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie aktualnych danych dawcy
    cur.execute("""
                SELECT imie, nazwisko, pesel, grupa_krwi, rh, kontakt
                FROM dawcy
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    dane = cur.fetchone()

    if request.method == "POST":
        imie = request.form["imie"]
        nazwisko = request.form["nazwisko"]
        pesel = request.form["pesel"]
        grupa = request.form["grupa"]
        rh = request.form["rh"]
        kontakt = request.form["kontakt"]

        cur.execute("""
                    UPDATE dawcy
                    SET imie = %s,
                        nazwisko = %s,
                        pesel = %s,
                        grupa_krwi = %s,
                        rh = %s,
                        kontakt = %s
                    WHERE id_uzytkownika = %s;
                    """, (imie, nazwisko, pesel, grupa, rh, kontakt, user_id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/dawca/dane")

    cur.close()
    conn.close()

    return render_template(
        "edytuj_dane_dawcy.html",
        imie=dane[0],
        nazwisko=dane[1],
        pesel=dane[2],
        grupa=dane[3],
        rh=dane[4],
        kontakt=dane[5]
    )


@app.route("/dawca/zgloszenia-oddania", methods=["GET", "POST"])
@login_required(role="DAWCA")
def zgloszenia_oddania():
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor()

    # Ustalamy id_dawcy na podstawie zalogowanego użytkownika
    cur.execute("""
                SELECT id_dawcy
                FROM dawcy
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return "Brak powiązanego dawcy dla tego użytkownika", 400

    id_dawcy = row[0]

    # Obsługa formularza - dodanie nowego zgłoszenia
    if request.method == "POST":
        data_zgloszenia = request.form.get("data_zgloszenia")

        # Jeśli użytkownik nie poda daty, ustawiamy dzisiejszą
        if not data_zgloszenia:
            cur.execute("SELECT CURRENT_DATE;")
            data_zgloszenia = cur.fetchone()[0]

        cur.execute("""
                    INSERT INTO zgloszenia (id_dawcy, data_zgloszenia, status)
                    VALUES (%s, %s, 'oczekujace');
                    """, (id_dawcy, data_zgloszenia))

        conn.commit()

        # po dodaniu zgłoszenia robimy redirect, żeby uniknąć ponownego submitu formularza
        cur.close()
        conn.close()
        return redirect("/dawca/zgloszenia-oddania")

    # Pobranie listy zgłoszeń danego dawcy
    cur.execute("""
                SELECT id_zgloszenia, data_zgloszenia, status
                FROM zgloszenia
                WHERE id_dawcy = %s
                ORDER BY data_zgloszenia DESC;
                """, (id_dawcy,))
    zgloszenia = cur.fetchall()

    # Pobranie historii oddań z widoku widok_magazyn
    # Zakładam, że w widoku jest kolumna 'dawca' (Imię Nazwisko)
    cur.execute("""
                SELECT id_oddania, dawca, grupa_krwi, rh, ilosc_ml, data_waznosci
                FROM widok_magazyn
                WHERE id_oddania IN (
                    SELECT id_oddania
                    FROM oddania_krwi
                    WHERE id_dawcy = %s
                )
                ORDER BY data_waznosci DESC;
                """, (id_dawcy,))
    oddania = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "zgloszenia_oddania.html",
        zgloszenia=zgloszenia,
        oddania=oddania
    )


@app.route("/pracownik")
@login_required(role="PRACOWNIK")
def panel_pracownika():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie danych pracownika
    cur.execute("""
                SELECT p.id_pracownika, p.imie, p.nazwisko, p.stanowisko
                FROM pracownicy_banku p
                WHERE p.id_uzytkownika = %s;
                """, (user_id,))
    pracownik = cur.fetchone()

    if not pracownik:
        cur.close()
        conn.close()
        return "Brak danych pracownika", 400

    id_pracownika = pracownik[0]

    # Pobranie statystyk z widoku widok_pracownicy_aktywnosc
    cur.execute("""
                SELECT liczba_oddan, liczba_badan, liczba_zapotrzebowan
                FROM widok_pracownicy_aktywnosc
                WHERE id_pracownika = %s;
                """, (id_pracownika,))
    statystyki = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "panel_pracownika.html",
        imie=pracownik[1],
        nazwisko=pracownik[2],
        stanowisko=pracownik[3],
        oddania=statystyki[0] if statystyki else 0,
        badania=statystyki[1] if statystyki else 0,
        zapotrzebowania=statystyki[2] if statystyki else 0
    )

@app.route("/pracownik/badania", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def badania():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie id_pracownika
    cur.execute("""
                SELECT id_pracownika
                FROM pracownicy_banku
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    id_pracownika = cur.fetchone()[0]

    # Dodawanie badania
    if request.method == "POST":
        id_oddania = request.form["id_oddania"]
        rodzaj = request.form["rodzaj"]
        wynik = request.form["wynik"]
        data_badania = request.form["data_badania"]

        cur.execute("""
                    INSERT INTO badania (id_oddania, id_pracownika, rodzaj_badania, wynik, data_badania)
                    VALUES (%s, %s, %s, %s, %s);
                    """, (id_oddania, id_pracownika, rodzaj, wynik, data_badania))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/pracownik/badania")

    # Pobranie badań z widoku
    cur.execute("""
                SELECT id_badania, id_oddania, dawca, rodzaj_badania, wynik, data_badania
                FROM widok_historia_badania
                ORDER BY data_badania DESC;
                """)
    badania = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("badania.html", badania=badania)

@app.route("/pracownik/badania/edytuj/<int:id_badania>", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def edytuj_badanie(id_badania):
    conn = get_db()
    cur = conn.cursor()

    # Pobranie danych badania
    cur.execute("""
                SELECT id_badania, id_oddania, rodzaj_badania, wynik, data_badania
                FROM badania
                WHERE id_badania = %s;
                """, (id_badania,))
    badanie = cur.fetchone()

    if request.method == "POST":
        rodzaj = request.form["rodzaj"]
        wynik = request.form["wynik"]
        data_badania = request.form["data_badania"]

        cur.execute("""
                    UPDATE badania
                    SET rodzaj_badania = %s,
                        wynik = %s,
                        data_badania = %s
                    WHERE id_badania = %s;
                    """, (rodzaj, wynik, data_badania, id_badania))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/pracownik/badania")

    cur.close()
    conn.close()

    return render_template("edytuj_badanie.html", badanie=badanie)

@app.route("/pracownik/badania/usun/<int:id_badania>")
@login_required(role="PRACOWNIK")
def usun_badanie(id_badania):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM badania WHERE id_badania = %s;", (id_badania,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect("/pracownik/badania")

@app.route("/pracownik/oddania", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def oddania():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie id_pracownika
    cur.execute("""
                SELECT id_pracownika
                FROM pracownicy_banku
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    id_pracownika = cur.fetchone()[0]

    # Dodawanie oddania
    if request.method == "POST":
        id_dawcy = request.form["id_dawcy"]
        ilosc_ml = request.form["ilosc_ml"]
        data_oddania = request.form["data_oddania"]

        cur.execute("""
                    INSERT INTO oddania_krwi (id_dawcy, id_pracownika, ilosc_ml, data_oddania)
                    VALUES (%s, %s, %s, %s);
                    """, (id_dawcy, id_pracownika, ilosc_ml, data_oddania))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/pracownik/oddania")

    # Pobranie oddań z widoku magazynu (ładniejsze dane)
    cur.execute("""
                SELECT id_oddania, dawca, grupa_krwi, rh, ilosc_ml, data_waznosci
                FROM widok_magazyn
                ORDER BY id_oddania DESC;
                """)
    oddania = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("oddania.html", oddania=oddania)

@app.route("/pracownik/oddania/edytuj/<int:id_oddania>", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def edytuj_oddanie(id_oddania):
    conn = get_db()
    cur = conn.cursor()

    # Pobranie danych oddania
    cur.execute("""
                SELECT id_oddania, id_dawcy, ilosc_ml, data_oddania
                FROM oddania_krwi
                WHERE id_oddania = %s;
                """, (id_oddania,))
    oddanie = cur.fetchone()

    if request.method == "POST":
        ilosc_ml = request.form["ilosc_ml"]
        data_oddania = request.form["data_oddania"]

        cur.execute("""
                    UPDATE oddania_krwi
                    SET ilosc_ml = %s,
                        data_oddania = %s
                    WHERE id_oddania = %s;
                    """, (ilosc_ml, data_oddania, id_oddania))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/pracownik/oddania")

    cur.close()
    conn.close()

    return render_template("edytuj_oddanie.html", oddanie=oddanie)

@app.route("/pracownik/oddania/usun/<int:id_oddania>")
@login_required(role="PRACOWNIK")
def usun_oddanie(id_oddania):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM oddania_krwi WHERE id_oddania = %s;", (id_oddania,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect("/pracownik/oddania")

@app.route("/pracownik/zapotrzebowania", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def zapotrzebowania():
    conn = get_db()
    cur = conn.cursor()

    # Zmiana statusu zapotrzebowania
    if request.method == "POST":
        id_zapotrzebowania = request.form["id_zapotrzebowania"]
        nowy_status = request.form["status"]

        cur.execute("""
                    UPDATE zapotrzebowania
                    SET status = %s
                    WHERE id_zapotrzebowania = %s;
                    """, (nowy_status, id_zapotrzebowania))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/pracownik/zapotrzebowania")

    # Pobranie listy zapotrzebowań
    cur.execute("""
                SELECT z.id_zapotrzebowania,
                       s.nazwa,
                       z.grupa_krwi,
                       z.rh,
                       z.ilosc_ml,
                       z.status,
                       z.data_wydania
                FROM zapotrzebowania z
                         JOIN szpitale s ON s.id_szpitala = z.id_szpitala
                ORDER BY z.data_wydania DESC;
                """)
    zapotrzebowania = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("zapotrzebowania.html", zapotrzebowania=zapotrzebowania)

@app.route("/pracownik/zapotrzebowania/zrealizuj/<int:id_zapotrzebowania>", methods=["POST"])
@login_required(role="PRACOWNIK")
def zrealizuj_zapotrzebowanie(id_zapotrzebowania):
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie id pracownika
    cur.execute("""
                SELECT id_pracownika
                FROM pracownicy_banku
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    id_pracownika = cur.fetchone()[0]

    # Pobranie zapotrzebowania
    cur.execute("""
                SELECT grupa_krwi, rh, ilosc_ml
                FROM zapotrzebowania
                WHERE id_zapotrzebowania = %s;
                """, (id_zapotrzebowania,))
    grupa, rh, ilosc_potrzebna = cur.fetchone()

    # 🔍 1. Sprawdzenie dostępnej ilości krwi w widoku
    cur.execute("""
                SELECT dostepne_ml
                FROM widok_stan_krwi
                WHERE grupa_krwi = %s AND rh = %s;
                """, (grupa, rh))
    wynik = cur.fetchone()

    if wynik is None or wynik[0] < ilosc_potrzebna:
        cur.close()
        conn.close()
        return "Brak wystarczającej ilości krwi w magazynie", 400

    # 🔍 2. Pobranie KONKRETNYCH oddań (FIFO)
    cur.execute("""
                SELECT o.id_oddania, o.ilosc_ml
                FROM oddania_krwi o
                         JOIN dawcy d ON o.id_dawcy = d.id_dawcy
                WHERE d.grupa_krwi = %s AND d.rh = %s
                ORDER BY o.data_oddania ASC;
                """, (grupa, rh))
    oddania = cur.fetchall()

    pozostalo = ilosc_potrzebna

    # 🔍 3. Odejmowanie krwi z oddań
    for id_oddania, ilosc_ml in oddania:
        if pozostalo <= 0:
            break

        if ilosc_ml <= pozostalo:
            # zużywamy całe oddanie
            cur.execute("""
                        INSERT INTO oddanie_zapotrzebowanie (id_oddania, id_zapotrzebowania, ilosc_ml)
                        VALUES (%s, %s, %s);
                        """, (id_oddania, id_zapotrzebowania, ilosc_ml))

            cur.execute("DELETE FROM oddania_krwi WHERE id_oddania = %s;", (id_oddania,))
            pozostalo -= ilosc_ml

        else:
            # zużywamy część oddania
            cur.execute("""
                        INSERT INTO oddanie_zapotrzebowanie (id_oddania, id_zapotrzebowania, ilosc_ml)
                        VALUES (%s, %s, %s);
                        """, (id_oddania, id_zapotrzebowania, pozostalo))

            nowa_ilosc = ilosc_ml - pozostalo
            cur.execute("""
                        UPDATE oddania_krwi
                        SET ilosc_ml = %s
                        WHERE id_oddania = %s;
                        """, (nowa_ilosc, id_oddania))

            pozostalo = 0

    # 🔍 4. Jeśli nadal brakuje krwi → rollback
    if pozostalo > 0:
        conn.rollback()
        cur.close()
        conn.close()
        return "Brak wystarczającej ilości krwi w magazynie", 400

    # 🔍 5. Aktualizacja statusu zapotrzebowania
    cur.execute("""
                UPDATE zapotrzebowania
                SET status = 'zrealizowane',
                    id_pracownika = %s
                WHERE id_zapotrzebowania = %s;
                """, (id_pracownika, id_zapotrzebowania))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/pracownik/zapotrzebowania")

@app.route("/pracownik/magazyn", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def magazyn():
    conn = get_db()
    cur = conn.cursor()

    grupa = None
    rh = None

    # Obsługa filtrowania
    if request.method == "POST":
        grupa = request.form.get("grupa")
        rh = request.form.get("rh")

        if grupa and rh:
            cur.execute("""
                        SELECT id_oddania, dawca, grupa_krwi, rh, ilosc_ml, data_waznosci
                        FROM widok_magazyn
                        WHERE grupa_krwi = %s AND rh = %s
                        ORDER BY data_waznosci DESC;
                        """, (grupa, rh))
        elif grupa:
            cur.execute("""
                        SELECT id_oddania, dawca, grupa_krwi, rh, ilosc_ml, data_waznosci
                        FROM widok_magazyn
                        WHERE grupa_krwi = %s
                        ORDER BY data_waznosci DESC;
                        """, (grupa,))
        else:
            cur.execute("""
                        SELECT id_oddania, dawca, grupa_krwi, rh, ilosc_ml, data_waznosci
                        FROM widok_magazyn
                        ORDER BY data_waznosci DESC;
                        """)
    else:
        # Domyślnie: pełny magazyn
        cur.execute("""
                    SELECT id_oddania, dawca, grupa_krwi, rh, ilosc_ml, data_waznosci
                    FROM widok_magazyn
                    ORDER BY data_waznosci DESC;
                    """)

    magazyn = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("magazyn.html", magazyn=magazyn)


@app.route("/szpital")
@login_required(role="SZPITAL")
def panel_szpitala():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie danych szpitala
    cur.execute("""
                SELECT id_szpitala, nazwa, adres
                FROM szpitale
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    szpital = cur.fetchone()

    if not szpital:
        cur.close()
        conn.close()
        return "Brak danych szpitala", 400

    id_szpitala = szpital[0]

    # Pobranie statystyk zapotrzebowań
    cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'oczekujace') AS oczekujace,
                    COUNT(*) FILTER (WHERE status = 'zrealizowane') AS zrealizowane,
                    COUNT(*) AS wszystkie
                FROM zapotrzebowania
                WHERE id_szpitala = %s;
                """, (id_szpitala,))
    statystyki = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "panel_szpitala.html",
        nazwa=szpital[1],
        adres=szpital[2],
        oczekujace=statystyki[0],
        zrealizowane=statystyki[1],
        wszystkie=statystyki[2]
    )

@app.route("/szpital/zapotrzebowania")
@login_required(role="SZPITAL")
def zapotrzebowania_szpitala():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie id szpitala
    cur.execute("""
                SELECT id_szpitala
                FROM szpitale
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    id_szpitala = cur.fetchone()[0]

    # Pobranie zapotrzebowań tego szpitala
    cur.execute("""
                SELECT id_zapotrzebowania,
                       grupa_krwi,
                       rh,
                       ilosc_ml,
                       status,
                       data_wydania
                FROM zapotrzebowania
                WHERE id_szpitala = %s
                ORDER BY data_wydania DESC;
                """, (id_szpitala,))
    zapotrzebowania = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("zapotrzebowania_szpitala.html",
                           zapotrzebowania=zapotrzebowania)

@app.route("/szpital/zapotrzebowania/dodaj", methods=["GET", "POST"])
@login_required(role="SZPITAL")
def dodaj_zapotrzebowanie():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie id szpitala
    cur.execute("""
                SELECT id_szpitala
                FROM szpitale
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    id_szpitala = cur.fetchone()[0]

    if request.method == "POST":
        grupa = request.form["grupa"]
        rh = request.form["rh"]
        ilosc_ml = request.form["ilosc_ml"]
        data_wydania = request.form["data_wydania"]

        cur.execute("""
                    INSERT INTO zapotrzebowania
                    (id_szpitala, grupa_krwi, rh, ilosc_ml, status, data_wydania, id_pracownika)
                    VALUES (%s, %s, %s, %s, 'oczekujace', %s, NULL);
                    """, (id_szpitala, grupa, rh, ilosc_ml, data_wydania))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/szpital/zapotrzebowania")

    cur.close()
    conn.close()

    return render_template("dodaj_zapotrzebowanie.html")


@app.route("/admin")
@login_required(role="ADMIN")
def panel_admina():
    conn = get_db()
    cur = conn.cursor()

    # Statystyki
    cur.execute("SELECT COUNT(*) FROM uzytkownicy;")
    uzytkownicy = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM dawcy;")
    dawcy = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pracownicy_banku;")
    pracownicy = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM szpitale;")
    szpitale = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM oddania_krwi;")
    oddania = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM zapotrzebowania;")
    zapotrzebowania = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM badania;")
    badania = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template(
        "panel_admina.html",
        uzytkownicy=uzytkownicy,
        dawcy=dawcy,
        pracownicy=pracownicy,
        szpitale=szpitale,
        oddania=oddania,
        zapotrzebowania=zapotrzebowania,
        badania=badania
    )


@app.route("/logout")
def logout():
    session.clear()
    return render_template("logout.html")


if __name__ == "__main__":
    app.run(debug=False)