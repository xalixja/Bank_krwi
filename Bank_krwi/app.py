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
            session["login"] = login

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

    #cel dawcy
    cur.execute("""
                SELECT cel_ml
                FROM dawcy
                WHERE id_dawcy = %s;
                """, (id_dawcy,))
    cel = cur.fetchone()[0]

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
        cel_ml=cel,
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
        kontakt = request.form["kontakt"]

        cur.execute("""
                    UPDATE dawcy
                    SET imie = %s,
                        nazwisko = %s,
                        pesel = %s,
                        kontakt = %s
                    WHERE id_uzytkownika = %s;
                    """, (imie, nazwisko, pesel, kontakt, user_id))

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
                SELECT id_oddania, dawca, grupa_krwi, rh,
                       ilosc_poczatkowa, ilosc_pozostala, status, data_waznosci
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

@app.route("/dawca/zgloszenia-oddania/usun/<int:id_zgloszenia>", methods=["POST"])
@login_required(role="DAWCA")
def usun_zgloszenie(id_zgloszenia):
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # upewniamy się, że zgłoszenie należy do tego dawcy i jest oczekujące
    cur.execute("""
                DELETE FROM zgloszenia
                WHERE id_zgloszenia = %s
                  AND id_dawcy = (SELECT id_dawcy FROM dawcy WHERE id_uzytkownika = %s)
                  AND status = 'oczekujace';
                """, (id_zgloszenia, user_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/dawca/zgloszenia-oddania")

@app.route("/dawca/cel", methods=["POST"])
@login_required(role="DAWCA")
def ustaw_cel():
    user_id = session["user_id"]
    cel = request.form["cel"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
                UPDATE dawcy
                SET cel_ml = %s
                WHERE id_uzytkownika = %s;
                """, (cel, user_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/dawca")


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

@app.route("/pracownik/dane")
@login_required(role="PRACOWNIK")
def dane_pracownika():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
                SELECT imie, nazwisko, stanowisko
                FROM pracownicy_banku
                WHERE id_uzytkownika = %s;
                """, (user_id,))

    dane = cur.fetchone()
    cur.close()
    conn.close()

    return render_template(
        "dane_pracownika.html",
        imie=dane[0],
        nazwisko=dane[1],
        stanowisko=dane[2],
    )

@app.route("/pracownik/dane/edytuj", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def edytuj_dane_pracownika():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie aktualnych danych pracownika
    cur.execute("""
                SELECT imie, nazwisko, stanowisko
                FROM pracownicy_banku
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    dane = cur.fetchone()

    if request.method == "POST":
        imie = request.form["imie"]
        nazwisko = request.form["nazwisko"]
        stanowisko = request.form["stanowisko"]

        cur.execute("""
                    UPDATE pracownicy_banku
                    SET imie = %s,
                        nazwisko = %s,
                        stanowisko = %s
                    WHERE id_uzytkownika = %s;
                    """, (imie, nazwisko, stanowisko, user_id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/pracownik/dane")

    cur.close()
    conn.close()

    return render_template(
        "edytuj_dane_pracownika.html",
        imie=dane[0],
        nazwisko=dane[1],
        stanowisko=dane[2]
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
                SELECT id_badania, id_oddania, dawca, rodzaj_badania, wynik, data_badania, id_pracownika
                FROM widok_historia_badania
                ORDER BY data_badania DESC;
                """)
    badania = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("badania.html", badania=badania, id_pracownika=id_pracownika)

@app.route("/pracownik/badania/edytuj/<int:id_badania>", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def edytuj_badanie(id_badania):
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie id_pracownika zalogowanego użytkownika
    cur.execute("""
                SELECT id_pracownika
                FROM pracownicy_banku
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    id_pracownika = cur.fetchone()[0]

    # Pobranie badania TYLKO jeśli wykonał je ten pracownik
    cur.execute("""
                SELECT id_badania, id_oddania, rodzaj_badania, wynik, data_badania
                FROM badania
                WHERE id_badania = %s
                  AND id_pracownika = %s;
                """, (id_badania, id_pracownika))

    badanie = cur.fetchone()

    # Jeśli badanie nie należy do pracownika → blokujemy dostęp
    if not badanie:
        cur.close()
        conn.close()
        return "Nie masz uprawnień do edycji tego badania.", 403

    # Obsługa formularza
    if request.method == "POST":
        rodzaj = request.form["rodzaj"]
        wynik = request.form["wynik"]
        data_badania = request.form["data_badania"]

        cur.execute("""
                    UPDATE badania
                    SET rodzaj_badania = %s,
                        wynik = %s,
                        data_badania = %s
                    WHERE id_badania = %s
                      AND id_pracownika = %s;
                    """, (rodzaj, wynik, data_badania, id_badania, id_pracownika))

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
                    INSERT INTO oddania_krwi (id_dawcy, id_pracownika, ilosc_ml, data_oddania, ilosc_pozostala)
                    VALUES (%s, %s, %s, %s, %s);
                    """, (id_dawcy, id_pracownika, ilosc_ml, data_oddania, ilosc_ml))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/pracownik/oddania")

    # Pobranie oddań
    cur.execute("""
                SELECT
                    o.id_oddania,
                    d.imie || ' ' || d.nazwisko AS dawca,
                    d.grupa_krwi,
                    d.rh,
                    o.ilosc_ml,
                    o.data_oddania,
                    o.data_waznosci
                FROM oddania_krwi o
                         JOIN dawcy d ON o.id_dawcy = d.id_dawcy
                ORDER BY o.id_oddania DESC;
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
                SELECT id_oddania, id_dawcy, ilosc_ml, data_oddania, ilosc_pozostala
                FROM oddania_krwi
                WHERE id_oddania = %s;
                """, (id_oddania,))
    oddanie = cur.fetchone()

    if request.method == "POST":
        ilosc_ml = request.form["ilosc_ml"]
        data_oddania = request.form["data_oddania"]
        ilosc_pozostala = request.form["ilosc_pozostala"]

        cur.execute("""
                    UPDATE oddania_krwi
                    SET ilosc_ml = %s,
                        data_oddania = %s
                    WHERE id_oddania = %s AND ilosc_ml>ilosc_pozostala;
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

    # -----------------------------
    # 1. ZMIANA STATUSU ZAPOTRZEBOWANIA
    # -----------------------------
    if request.method == "POST" and "id_zapotrzebowania" in request.form:
        id_zapotrzebowania = request.form["id_zapotrzebowania"]
        nowy_status = request.form["nowy_status"]

        cur.execute("""
                    UPDATE zapotrzebowania
                    SET status = %s
                    WHERE id_zapotrzebowania = %s;
                    """, (nowy_status, id_zapotrzebowania))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/pracownik/zapotrzebowania")

    # -----------------------------
    # 2. FILTROWANIE
    # -----------------------------
    filter_status = request.form.get("filter_status") if request.method == "POST" else None

    base_query = """
                 SELECT z.id_zapotrzebowania,
                        s.nazwa,
                        z.grupa_krwi,
                        z.rh,
                        z.ilosc_ml,
                        z.status,
                        z.data_wydania
                 FROM zapotrzebowania z
                          JOIN szpitale s ON s.id_szpitala = z.id_szpitala \
                 """

    if filter_status and filter_status != "wszystkie":
        cur.execute(base_query + " WHERE z.status = %s ORDER BY z.data_wydania DESC;", (filter_status,))
    else:
        cur.execute(base_query + " ORDER BY z.data_wydania DESC;")

    zapotrzebowania = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("zapotrzebowania.html",
                           zapotrzebowania=zapotrzebowania,
                           filter_status=filter_status)


@app.route("/pracownik/zapotrzebowania/zrealizuj/<int:id_zapotrzebowania>", methods=["POST"])
@login_required(role="PRACOWNIK")
def zrealizuj_zapotrzebowanie(id_zapotrzebowania):
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    try:
        # 1. Id pracownika
        cur.execute("""
                    SELECT id_pracownika
                    FROM pracownicy_banku
                    WHERE id_uzytkownika = %s;
                    """, (user_id,))
        id_pracownika = cur.fetchone()[0]

        # 2. Zapotrzebowanie - POBIERAMY TEŻ STATUS
        cur.execute("""
                    SELECT grupa_krwi, rh, ilosc_ml, status
                    FROM zapotrzebowania
                    WHERE id_zapotrzebowania = %s;
                    """, (id_zapotrzebowania,))
        dane_zapotrzebowania = cur.fetchone()

        if not dane_zapotrzebowania:
            return "Nie znaleziono zapotrzebowania", 404

        grupa, rh, ilosc_potrzebna, status = dane_zapotrzebowania

        # --- ZABEZPIECZENIE 1: Sprawdź czy już nie zrealizowane ---
        if status == 'zrealizowane':
            cur.close()
            conn.close()
            # Możesz przekierować z komunikatem flash zamiast return string
            return "To zapotrzebowanie zostało już zrealizowane!", 400

        # 3. Sprawdzenie stanu magazynowego
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

        # 4. Pobranie oddań (FIFO)
        cur.execute("""
                    SELECT id_oddania, ilosc_pozostala
                    FROM widok_magazyn
                    WHERE grupa_krwi = %s
                      AND rh = %s
                      AND status = 'dostepne'
                      AND ilosc_pozostala > 0
                    ORDER BY data_waznosci ASC;
                    """, (grupa, rh))
        oddania = cur.fetchall()

        pozostalo = ilosc_potrzebna

        for id_oddania, ilosc_pozostala in oddania:
            if pozostalo <= 0:
                break

            # Oblicz ile bierzemy z tego worka
            ilosc_do_pobrania = min(ilosc_pozostala, pozostalo)

            # --- ZABEZPIECZENIE 2: INSERT ON CONFLICT (Dla PostgreSQL) ---
            # Jeśli wpis już istnieje (np. po błędzie), aktualizujemy go zamiast wyrzucać błąd
            cur.execute("""
                        INSERT INTO oddanie_zapotrzebowanie (id_oddania, id_zapotrzebowania, ilosc_ml)
                        VALUES (%s, %s, %s)
                            ON CONFLICT (id_oddania, id_zapotrzebowania) 
                        DO UPDATE SET ilosc_ml = oddanie_zapotrzebowanie.ilosc_ml + EXCLUDED.ilosc_ml;
                        """, (id_oddania, id_zapotrzebowania, ilosc_do_pobrania))

            # Aktualizacja magazynu (oddania)
            if ilosc_pozostala <= pozostalo:
                # Zużywamy całe oddanie
                cur.execute("""
                            UPDATE oddania_krwi
                            SET ilosc_pozostala = 0,
                                status = 'zuzyte'
                            WHERE id_oddania = %s;
                            """, (id_oddania,))
            else:
                # Zużywamy część
                nowa_pozostala = ilosc_pozostala - pozostalo
                cur.execute("""
                            UPDATE oddania_krwi
                            SET ilosc_pozostala = %s
                            WHERE id_oddania = %s;
                            """, (nowa_pozostala, id_oddania))

            pozostalo -= ilosc_do_pobrania

        if pozostalo > 0:
            conn.rollback() # Cofamy wszystko jeśli nie udało się uzbierać całości
            cur.close()
            conn.close()
            return "Brak wystarczającej ilości krwi w magazynie (błąd spójności)", 400

        # 5. Aktualizacja zapotrzebowania
        cur.execute("""
                    UPDATE zapotrzebowania
                    SET status = 'zrealizowane',
                        id_pracownika = %s,
                        data_wydania = NOW()
                    WHERE id_zapotrzebowania = %s;
                    """, (id_pracownika, id_zapotrzebowania))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/pracownik/zapotrzebowania")

    except Exception as e:
        conn.rollback() # Bardzo ważne: rollback przy każdym błędzie
        cur.close()
        conn.close()
        raise e # Rzuć błąd dalej, żeby widzieć go w konsoli


@app.route("/pracownik/magazyn", methods=["GET", "POST"])
@login_required(role="PRACOWNIK")
def magazyn():
    conn = get_db()
    cur = conn.cursor()

    grupa = request.form.get("grupa") if request.method == "POST" else None
    rh = request.form.get("rh") if request.method == "POST" else None

    # --- 1. KREW DOSTĘPNA (z filtrowaniem) ---
    base_query = """
                 SELECT id_oddania, dawca, grupa_krwi, rh,
                        ilosc_poczatkowa, ilosc_pozostala, status, data_waznosci
                 FROM widok_magazyn
                 WHERE status = 'dostepne' \
                 """

    if grupa and rh:
        cur.execute(base_query + " AND grupa_krwi = %s AND rh = %s ORDER BY data_waznosci ASC;",
                    (grupa, rh))
    elif grupa:
        cur.execute(base_query + " AND grupa_krwi = %s ORDER BY data_waznosci ASC;",
                    (grupa,))
    else:
        cur.execute(base_query + " ORDER BY data_waznosci ASC;")

    dostepne = cur.fetchall()

    # --- 2. KREW PRZETERMINOWANA ---
    cur.execute("""
                SELECT id_oddania, dawca, grupa_krwi, rh,
                       ilosc_poczatkowa, ilosc_pozostala, status, data_waznosci
                FROM widok_magazyn
                WHERE status = 'przeterminowane'
                ORDER BY data_waznosci ASC;
                """)
    przeterminowane = cur.fetchall()

    # --- 3. KREW ZUŻYTA ---
    cur.execute("""
                SELECT id_oddania, dawca, grupa_krwi, rh,
                       ilosc_poczatkowa, ilosc_pozostala, status, data_waznosci
                FROM widok_magazyn
                WHERE status = 'zuzyte'
                ORDER BY data_waznosci ASC;
                """)
    zuzyte = cur.fetchall()

    # --- 3. KREW ODRZUCONA ---
    cur.execute("""
                SELECT id_oddania, dawca, grupa_krwi, rh,
                       ilosc_poczatkowa, ilosc_pozostala, status, data_waznosci
                FROM widok_magazyn
                WHERE status = 'odrzucone_badanie'
                ORDER BY data_waznosci ASC;
                """)
    odrzucone = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "magazyn.html",
        dostepne=dostepne,
        przeterminowane=przeterminowane,
        zuzyte=zuzyte,
        odrzucone=odrzucone
    )




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

@app.route("/szpital/dane")
@login_required(role="SZPITAL")
def dane_szpitala():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
                SELECT nazwa, adres
                FROM szpitale
                WHERE id_uzytkownika = %s;
                """, (user_id,))

    dane = cur.fetchone()
    cur.close()
    conn.close()

    return render_template(
        "dane_szpitala.html",
        nazwa=dane[0],
        adres=dane[1],
    )

@app.route("/szpital/dane/edytuj", methods=["GET", "POST"])
@login_required(role="SZPITAL")
def edytuj_dane_szpitala():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Pobranie aktualnych danych szpitala
    cur.execute("""
                SELECT nazwa, adres
                FROM szpitale
                WHERE id_uzytkownika = %s;
                """, (user_id,))
    dane = cur.fetchone()

    if request.method == "POST":
        nazwa = request.form["nazwa"]
        adres = request.form["adres"]

        cur.execute("""
                    UPDATE szpitale
                    SET nazwa = %s,
                        adres = %s
                    WHERE id_uzytkownika = %s;
                    """, (nazwa, adres, user_id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/szpital/dane")

    cur.close()
    conn.close()

    return render_template(
        "edytuj_dane_szpitala.html",
        nazwa=dane[0],
        adres=dane[1],
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

@app.route("/szpital/zapotrzebowania/edytuj/<int:id_zapotrzebowania>", methods=["POST"])
@login_required(role="SZPITAL")
def edytuj_zapotrzebowanie_szpital(id_zapotrzebowania):
    user_id = session["user_id"]

    grupa = request.form["grupa"]
    rh = request.form["rh"]
    ilosc_ml = request.form["ilosc_ml"]

    conn = get_db()
    cur = conn.cursor()

    # upewniamy się, że zapotrzebowanie należy do tego szpitala i jest oczekujące
    cur.execute("""
                UPDATE zapotrzebowania
                SET grupa_krwi = %s,
                    rh = %s,
                    ilosc_ml = %s
                WHERE id_zapotrzebowania = %s
                  AND id_szpitala = (SELECT id_szpitala FROM szpitale WHERE id_uzytkownika = %s)
                  AND status = 'oczekujace';
                """, (grupa, rh, ilosc_ml, id_zapotrzebowania, user_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/szpital/zapotrzebowania")

@app.route("/szpital/zapotrzebowania/usun/<int:id_zapotrzebowania>", methods=["POST"])
@login_required(role="SZPITAL")
def usun_zapotrzebowanie_szpital(id_zapotrzebowania):
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
                DELETE FROM zapotrzebowania
                WHERE id_zapotrzebowania = %s
                  AND id_szpitala = (SELECT id_szpitala FROM szpitale WHERE id_uzytkownika = %s)
                  AND status = 'oczekujace';
                """, (id_zapotrzebowania, user_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/szpital/zapotrzebowania")


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

@app.route("/admin/uzytkownicy")
@login_required(role="ADMIN")
def admin_uzytkownicy():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
                SELECT id_uzytkownika, login, rola, data_rejestracji
                FROM uzytkownicy
                ORDER BY id_uzytkownika;
                """)
    uzytkownicy = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_uzytkownicy.html", uzytkownicy=uzytkownicy)

@app.route("/admin/uzytkownicy/dodaj", methods=["POST"])
@login_required(role="ADMIN")
def admin_uzytkownicy_dodaj():
    login = request.form["login"]
    haslo = request.form["haslo"]
    rola = request.form["rola"]

    conn = get_db()
    cur = conn.cursor()

    # 1. Dodajemy użytkownika
    cur.execute("""
                INSERT INTO uzytkownicy (login, haslo, rola)
                VALUES (%s, public.crypt(%s, public.gen_salt('bf')), %s)
                    RETURNING id_uzytkownika;
                """, (login, haslo, rola))

    id_uzytkownika = cur.fetchone()[0]

    # 2. W zależności od roli dodajemy dane do odpowiedniej tabeli

    if rola == "DAWCA":
        cur.execute("""
                    INSERT INTO dawcy (imie, nazwisko, pesel, grupa_krwi, rh, kontakt, id_uzytkownika)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        request.form["d_imie"],
                        request.form["d_nazwisko"],
                        request.form["d_pesel"],
                        request.form["d_grupa"],
                        request.form["d_rh"],
                        request.form["d_kontakt"],
                        id_uzytkownika
                    ))

    elif rola == "PRACOWNIK":
        cur.execute("""
                    INSERT INTO pracownicy_banku (imie, nazwisko, stanowisko, id_uzytkownika)
                    VALUES (%s, %s, %s, %s);
                    """, (
                        request.form["p_imie"],
                        request.form["p_nazwisko"],
                        request.form["p_stanowisko"],
                        id_uzytkownika
                    ))

    elif rola == "SZPITAL":
        cur.execute("""
                    INSERT INTO szpitale (nazwa, adres, id_uzytkownika)
                    VALUES (%s, %s, %s);
                    """, (
                        request.form["s_nazwa"],
                        request.form["s_adres"],
                        id_uzytkownika
                    ))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/uzytkownicy")

@app.route("/admin/uzytkownicy/edytuj/<int:id_uzytkownika>", methods=["POST"])
@login_required(role="ADMIN")
def admin_uzytkownicy_edytuj(id_uzytkownika):
    login = request.form["login"]
    haslo = request.form["haslo"]

    conn = get_db()
    cur = conn.cursor()

    if haslo.strip() == "":
        # zmiana tylko loginu
        cur.execute("""
                    UPDATE uzytkownicy
                    SET login = %s
                    WHERE id_uzytkownika = %s;
                    """, (login, id_uzytkownika))
    else:
        # zmiana loginu i hasła
        cur.execute("""
                    UPDATE uzytkownicy
                    SET login = %s,
                        haslo = public.crypt(%s, gen_salt('bf'))
                    WHERE id_uzytkownika = %s;
                    """, (login, haslo, id_uzytkownika))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/uzytkownicy")


@app.route("/admin/uzytkownicy/usun/<int:id_uzytkownika>", methods=["POST"])
@login_required(role="ADMIN")
def admin_uzytkownicy_usun(id_uzytkownika):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM uzytkownicy WHERE id_uzytkownika = %s;", (id_uzytkownika,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/admin/uzytkownicy")

@app.route("/uzytkownik/edytuj", methods=["POST"])
@login_required()
def edytuj_uzytkownika():
    user_id = session["user_id"]
    login = request.form["login"]
    haslo = request.form["haslo"]

    conn = get_db()
    cur = conn.cursor()

    if haslo.strip() == "":
        cur.execute("""
                    UPDATE uzytkownicy
                    SET login = %s
                    WHERE id_uzytkownika = %s;
                    """, (login, user_id))
    else:
        cur.execute("""
                    UPDATE uzytkownicy
                    SET login = %s,
                        haslo = crypt(%s, gen_salt('bf'))
                    WHERE id_uzytkownika = %s;
                    """, (login, haslo, user_id))

    conn.commit()
    cur.close()
    conn.close()

    session["login"] = login

    # wracamy do panelu zależnie od roli
    rola = session["rola"]
    if rola == "DAWCA":
        return redirect("/dawca")
    if rola == "PRACOWNIK":
        return redirect("/pracownik")
    if rola == "SZPITAL":
        return redirect("/szpital")
    if rola == "ADMIN":
        return redirect("/admin")


    return render_template("dane_konta.html", uzytkownicy=uzytkownicy)
@app.route("/logout")
def logout():
    session.clear()
    return render_template("logout.html")


if __name__ == "__main__":
    app.run(debug=False)