-- włącz rozszerzenie pgcrypto
create extension if not exists pgcrypto;

-- utworzenie schematu
create schema if not exists bank_krwi;
set search_path to bank_krwi, public;

-- tabele główne
create table Uzytkownicy (
    id_uzytkownika serial primary key,
    login varchar(50) not null unique,
    haslo varchar(200) not null,
    rola varchar(20) check (rola in ('ADMIN','PRACOWNIK','SZPITAL','DAWCA')),
    data_rejestracji date default current_date
);

create table Dawcy (
    id_dawcy serial primary key,
    imie varchar(30) not null,
    nazwisko varchar(30) not null,
    pesel varchar(11) unique not null,
    grupa_krwi varchar(2) check (grupa_krwi in ('A','B','AB','0')),
    rh varchar(1) check (rh in ('+','-')),
    kontakt varchar(9),
    id_uzytkownika int unique references Uzytkownicy(id_uzytkownika),
    cel_ml int default 0 CHECK (cel_ml BETWEEN 0 AND 126900)
);

create table Pracownicy_banku (
    id_pracownika serial primary key,
    imie varchar(30) not null,
    nazwisko varchar(30) not null,
    stanowisko varchar(20) check (stanowisko in ('lekarz','laborant')),
    id_uzytkownika int unique references Uzytkownicy(id_uzytkownika)
);

create table Szpitale (
    id_szpitala serial primary key,
    nazwa varchar(100) not null,
    adres varchar(200),
    id_uzytkownika int unique references Uzytkownicy(id_uzytkownika)
);

create table Zgloszenia (
    id_zgloszenia serial primary key,
    id_dawcy int references Dawcy(id_dawcy),
    data_zgloszenia date default current_date,
    status varchar(20) check (status in ('oczekujace','zrealizowane'))
);

create table Oddania_krwi (
    id_oddania serial primary key,
    data_oddania date not null,
    ilosc_ml int check (ilosc_ml between 200 and 500),
    data_waznosci date,
    id_dawcy int references Dawcy(id_dawcy),
    id_zgloszenia int references Zgloszenia(id_zgloszenia),
    id_pracownika int references Pracownicy_banku(id_pracownika),
    ilosc_pozostala int default 0,
    status varchar(20) default 'dostepne' check (status in('dostepne','zuzyte','przeterminowane','odrzucone_badanie'))
);

create table Zapotrzebowania (
    id_zapotrzebowania serial primary key,
    id_szpitala int references Szpitale(id_szpitala),
    grupa_krwi varchar(2) check (grupa_krwi in ('A','B','AB','0')),
    rh varchar(1) check (rh in ('+','-')),
    ilosc_ml int check (ilosc_ml > 0),
    status varchar(20) check (status in ('oczekujace','zrealizowane')),
    data_wydania date,
    id_pracownika int references Pracownicy_banku(id_pracownika)
);

create table Badania (
    id_badania serial primary key,
    id_oddania int references Oddania_krwi(id_oddania),
    rodzaj_badania varchar(50) not null,
    wynik varchar(50) check (wynik in('pozytywny', 'negatywny')),
    data_badania date,
    id_pracownika int references Pracownicy_banku(id_pracownika)
);


-- tabele asocjacyjne (n-m)
create table Oddanie_Zapotrzebowanie (
    id_oddania int references Oddania_krwi(id_oddania),
    id_zapotrzebowania int references Zapotrzebowania(id_zapotrzebowania),
    ilosc_ml int check (ilosc_ml > 0),
    primary key (id_oddania, id_zapotrzebowania)
);

create table Dawca_Szpital (
    id_dawcy int references Dawcy(id_dawcy),
    id_szpitala int references Szpitale(id_szpitala),
    id_oddania int references Oddania_krwi(id_oddania),
    data_przekazania date,
    primary key (id_dawcy, id_szpitala, id_oddania)
);


--dodawanie danych testowych
-- Uzytkownicy
insert into Uzytkownicy (login, haslo, rola) values
('admin1', crypt('adminpass', gen_salt('bf')), 'ADMIN'),
('pracownik1', crypt('pracpass', gen_salt('bf')), 'PRACOWNIK'),
('pracownik2', crypt('pracpass2', gen_salt('bf')), 'PRACOWNIK'),
('szpital1', crypt('szpitpass', gen_salt('bf')), 'SZPITAL'),
('dawca1', crypt('dawcapass', gen_salt('bf')), 'DAWCA'),
('dawca2', crypt('dawcapass2', gen_salt('bf')), 'DAWCA');

INSERT INTO Uzytkownicy (login, haslo, rola)
VALUES ('admin2', crypt('admin123', gen_salt('bf')), 'ADMIN');

-- Dawcy (wiążemy po loginie)
insert into Dawcy (imie, nazwisko, pesel, grupa_krwi, rh, kontakt, id_uzytkownika) values
('Jan',  'Kowalski', '90010112345', 'A',  '+', '123456789',
 (select id_uzytkownika from Uzytkownicy where login='dawca1')),
('Anna', 'Nowak',    '92050567890', '0',  '-', '987654321',
 (select id_uzytkownika from Uzytkownicy where login='dawca2'));

-- Pracownicy_banku
insert into Pracownicy_banku (imie, nazwisko, stanowisko, id_uzytkownika) values
('Piotr', 'Lekarz',   'lekarz',   (select id_uzytkownika from Uzytkownicy where login='pracownik1')),
('Maria', 'Laborant', 'laborant', (select id_uzytkownika from Uzytkownicy where login='pracownik2'));

-- Szpitale
insert into Szpitale (nazwa, adres, id_uzytkownika) values
('Szpital Uniwersytecki', 'Kraków, ul. Kopernika 36', (select id_uzytkownika from Uzytkownicy where login='szpital1'));

-- Zgloszenia (po peselu dawcy)
with d as (
  select id_dawcy from Dawcy where pesel in ('90010112345','92050567890')
)
insert into Zgloszenia (id_dawcy, data_zgloszenia, status) values
((select id_dawcy from Dawcy where pesel='90010112345'), '2025-12-01', 'zrealizowane'),
((select id_dawcy from Dawcy where pesel='92050567890'), '2025-12-02', 'oczekujace');

-- Oddania_krwi
insert into Oddania_krwi (data_oddania, ilosc_ml, data_waznosci, id_dawcy, id_zgloszenia, id_pracownika) values
('2025-12-03', 450, '2026-01-14',
 (select id_dawcy from Dawcy where pesel='90010112345'),
 (select id_zgloszenia from Zgloszenia where id_dawcy = (select id_dawcy from Dawcy where pesel='90010112345')),
 (select id_pracownika from Pracownicy_banku where id_uzytkownika = (select id_uzytkownika from Uzytkownicy where login='pracownik1'))),
('2025-12-04', 500, '2026-01-15',
 (select id_dawcy from Dawcy where pesel='92050567890'),
 (select id_zgloszenia from Zgloszenia where id_dawcy = (select id_dawcy from Dawcy where pesel='92050567890')),
 (select id_pracownika from Pracownicy_banku where id_uzytkownika = (select id_uzytkownika from Uzytkownicy where login='pracownik1')));

-- Badania (po ostatnim oddaniu i pracowniku)
insert into Badania (id_oddania, rodzaj_badania, wynik, data_badania, id_pracownika) values
((select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='90010112345') order by id_oddania limit 1),
 'HIV', 'negatywny', '2025-12-05',
 (select id_pracownika from Pracownicy_banku where id_uzytkownika = (select id_uzytkownika from Uzytkownicy where login='pracownik2'))),
((select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='90010112345') order by id_oddania limit 1),
 'HBV', 'negatywny', '2025-12-05',
 (select id_pracownika from Pracownicy_banku where id_uzytkownika = (select id_uzytkownika from Uzytkownicy where login='pracownik2'))),
((select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='92050567890') order by id_oddania limit 1),
 'HCV', 'negatywny', '2025-12-06',
 (select id_pracownika from Pracownicy_banku where id_uzytkownika = (select id_uzytkownika from Uzytkownicy where login='pracownik2')));

-- Zapotrzebowania
insert into Zapotrzebowania (id_szpitala, grupa_krwi, rh, ilosc_ml, status) values
((select id_szpitala from Szpitale where nazwa='Szpital Uniwersytecki'), 'A', '+', 300, 'oczekujace'),
((select id_szpitala from Szpitale where nazwa='Szpital Uniwersytecki'), '0', '-', 500, 'zrealizowane');

-- Oddanie_Zapotrzebowanie (łączymy po grupie/rh i ostatnich ID)
insert into Oddanie_Zapotrzebowanie (id_oddania, id_zapotrzebowania, ilosc_ml) values
((select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='90010112345') order by id_oddania limit 1),
 (select id_zapotrzebowania from Zapotrzebowania where grupa_krwi='A' and rh='+'),
 300),
((select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='92050567890') order by id_oddania limit 1),
 (select id_zapotrzebowania from Zapotrzebowania where grupa_krwi='0' and rh='-'),
 500);

-- Dawca_Szpital
insert into Dawca_Szpital (id_dawcy, id_szpitala, id_oddania, data_przekazania) values
((select id_dawcy from Dawcy where pesel='90010112345'),
 (select id_szpitala from Szpitale where nazwa='Szpital Uniwersytecki'),
 (select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='90010112345') order by id_oddania limit 1),
 '2025-12-07'),
((select id_dawcy from Dawcy where pesel='92050567890'),
 (select id_szpitala from Szpitale where nazwa='Szpital Uniwersytecki'),
 (select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='92050567890') order by id_oddania limit 1),
 '2025-12-08');

--wazne
UPDATE oddania_krwi
SET ilosc_pozostala = ilosc_ml;


--widoki
CREATE OR REPLACE VIEW widok_magazyn AS
SELECT
    o.id_oddania,
    d.imie || ' ' || d.nazwisko AS dawca,
    d.grupa_krwi,
    d.rh,
    o.ilosc_ml AS ilosc_poczatkowa,
    o.ilosc_pozostala,
    o.status,
    o.data_waznosci
FROM oddania_krwi o
JOIN dawcy d ON o.id_dawcy = d.id_dawcy;

create view Widok_status_zapotrzebowan as
select z.id_zapotrzebowania,
       s.nazwa as szpital,
       z.grupa_krwi,
       z.rh,
       z.ilosc_ml,
       z.status,
       z.data_wydania,
       p.imie || ' ' || p.nazwisko as pracownik
from Zapotrzebowania z
join Szpitale s on z.id_szpitala = s.id_szpitala
left join Pracownicy_banku p on z.id_pracownika = p.id_pracownika;

CREATE OR REPLACE VIEW widok_historia_badania AS
SELECT 
    b.id_badania,
    o.id_oddania,
    d.imie || ' ' || d.nazwisko AS dawca,
    b.rodzaj_badania,
    b.wynik,
    b.data_badania,
    p.imie || ' ' || p.nazwisko AS pracownik,
    p.id_pracownika
FROM Badania b
JOIN Oddania_krwi o ON b.id_oddania = o.id_oddania
JOIN Dawcy d ON o.id_dawcy = d.id_dawcy
JOIN Pracownicy_banku p ON b.id_pracownika = p.id_pracownika;

create view Widok_dawcy_szpitale as
SELECT 
    ds.id_dawcy,
    d.imie || ' ' || d.nazwisko AS dawca,
    s.nazwa AS szpital,
    ds.data_przekazania,
    o.ilosc_ml AS ilosc_oddana
FROM dawca_szpital ds
JOIN dawcy d ON ds.id_dawcy = d.id_dawcy
JOIN szpitale s ON ds.id_szpitala = s.id_szpitala
JOIN oddania_krwi o ON ds.id_oddania = o.id_oddania;

create view Widok_pracownicy_aktywnosc as
select p.id_pracownika,
       p.imie || ' ' || p.nazwisko as pracownik,
       p.stanowisko,
       count(distinct o.id_oddania) as liczba_oddan,
       count(distinct b.id_badania) as liczba_badan,
       count(distinct z.id_zapotrzebowania) as liczba_zapotrzebowan
from Pracownicy_banku p
left join Oddania_krwi o on p.id_pracownika = o.id_pracownika
left join Badania b on p.id_pracownika = b.id_pracownika
left join Zapotrzebowania z on p.id_pracownika = z.id_pracownika
group by p.id_pracownika, p.imie, p.nazwisko, p.stanowisko;

create view Widok_zapotrzebowania_duze as
select s.nazwa as szpital,
       z.grupa_krwi,
       z.rh,
       sum(z.ilosc_ml) as suma_ml
from Zapotrzebowania z
join Szpitale s on z.id_szpitala = s.id_szpitala
group by s.nazwa, z.grupa_krwi, z.rh
having sum(z.ilosc_ml) > 1000;

CREATE OR REPLACE VIEW widok_srednia_ilosc AS
SELECT ROUND(AVG(o.ilosc_ml), 2) AS srednia_ml
FROM oddania_krwi o;

create view Widok_dat_oddan as
select id_dawcy, 
		min(data_oddania) as pierwsze_oddanie,
       max(data_oddania) as ostatnie_oddanie
from Oddania_krwi
group by 1;

create view Widok_statystyki_badan as
select 
    count(*) filter (where wynik = 'negatywny') as negatywne,
    count(*) filter (where wynik = 'pozytywny') as pozytywne
from Badania;

CREATE OR REPLACE VIEW widok_stan_krwi AS
SELECT
    d.grupa_krwi,
    d.rh,
    SUM(o.ilosc_pozostala) AS dostepne_ml
FROM oddania_krwi o
JOIN dawcy d ON o.id_dawcy = d.id_dawcy
WHERE o.status = 'dostepne'
  AND o.ilosc_pozostala > 0
GROUP BY d.grupa_krwi, d.rh;

CREATE VIEW widok_suma_ml AS
SELECT 
    id_dawcy,
    SUM(ilosc_ml) AS suma_ml
FROM oddania_krwi
GROUP BY id_dawcy;

CREATE OR REPLACE VIEW widok_powiazania AS
SELECT 
    oz.id_oddania,
    o.data_oddania,
    o.ilosc_ml AS ilosc_oddana,
    oz.ilosc_ml AS ilosc_przekazana,
    oz.id_zapotrzebowania,
    z.data_wydania AS data_zapotrzebowania,
    s.nazwa AS szpital
FROM oddanie_zapotrzebowanie oz
JOIN oddania_krwi o ON oz.id_oddania = o.id_oddania
JOIN zapotrzebowania z ON oz.id_zapotrzebowania = z.id_zapotrzebowania
JOIN szpitale s ON z.id_szpitala = s.id_szpitala
ORDER BY oz.id_zapotrzebowania DESC;


--triggery
create or replace function set_data_wydania()
returns trigger as $$
begin
    if NEW.status = 'zrealizowane' and NEW.data_wydania is null then
        NEW.data_wydania := current_date;
    end if;
    return NEW;
end;
$$ language plpgsql;

create trigger trg_set_data_wydania
before insert or update on Zapotrzebowania
for each row
execute function set_data_wydania();

CREATE OR REPLACE FUNCTION ustaw_date_waznosci()
RETURNS trigger AS $$
BEGIN
    -- ZAWSZE ustawiamy datę ważności na 35 dni od daty oddania
    NEW.data_waznosci := NEW.data_oddania + INTERVAL '35 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_oddania_data_waznosci
BEFORE INSERT OR UPDATE ON oddania_krwi
FOR EACH ROW
EXECUTE FUNCTION ustaw_date_waznosci();

CREATE OR REPLACE FUNCTION oznacz_przeterminowane()
RETURNS trigger AS $$
BEGIN
    IF NEW.data_waznosci < CURRENT_DATE THEN
        NEW.status := 'przeterminowane';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_przeterminowane
BEFORE UPDATE OR INSERT ON oddania_krwi
FOR EACH ROW
EXECUTE FUNCTION oznacz_przeterminowane();

CREATE OR REPLACE FUNCTION oznacz_odrzucone_badanie()
RETURNS trigger AS $$
BEGIN
    -- Jeśli wynik badania jest pozytywny → odrzucamy jednostkę
    IF NEW.wynik = 'pozytywny' THEN
        UPDATE oddania_krwi
        SET status = 'odrzucone_badanie'
        WHERE id_oddania = NEW.id_oddania;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_odrzucone_badanie
AFTER INSERT OR UPDATE ON badania
FOR EACH ROW
EXECUTE FUNCTION oznacz_odrzucone_badanie();

CREATE OR REPLACE FUNCTION przyjmij_najstarsze_zgloszenie()
RETURNS trigger AS $$
BEGIN
    -- Aktualizujemy najstarsze oczekujące zgłoszenie danego dawcy
    UPDATE zgloszenia
    SET status = 'zrealizowane'
    WHERE id_zgloszenia = (
        SELECT id_zgloszenia
        FROM zgloszenia
        WHERE id_dawcy = NEW.id_dawcy
          AND status = 'oczekujace'
        ORDER BY data_zgloszenia ASC
        LIMIT 1
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_przyjmij_zgloszenie
AFTER INSERT ON oddania_krwi
FOR EACH ROW
EXECUTE FUNCTION przyjmij_najstarsze_zgloszenie();

CREATE OR REPLACE FUNCTION blokuj_wiele_zgloszen()
RETURNS trigger AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM zgloszenia
        WHERE id_dawcy = NEW.id_dawcy
          AND status = 'oczekujace'
    ) THEN
        RAISE EXCEPTION 'Dawca ma już aktywne zgłoszenie.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_1_blokuj_wiele_zgloszen
BEFORE INSERT ON zgloszenia
FOR EACH ROW
EXECUTE FUNCTION blokuj_wiele_zgloszen();

CREATE OR REPLACE FUNCTION blokuj_wczesne_zgloszenie()
RETURNS trigger AS $$
DECLARE
    ostatnie DATE;
BEGIN
    SELECT data_oddania INTO ostatnie
    FROM oddania_krwi
    WHERE id_dawcy = NEW.id_dawcy
    ORDER BY data_oddania DESC
    LIMIT 1;

    IF ostatnie IS NOT NULL AND NEW.data_zgloszenia < ostatnie + INTERVAL '56 days' THEN
        RAISE EXCEPTION 'Możesz oddać krew dopiero po %', ostatnie + INTERVAL '56 days';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2_blokuj_wczesne_oddanie
BEFORE INSERT ON zgloszenia
FOR EACH ROW
EXECUTE FUNCTION blokuj_wczesne_zgloszenie();

CREATE OR REPLACE FUNCTION blokuj_wczesne_oddanie()
RETURNS trigger AS $$
DECLARE
    ostatnie DATE;
BEGIN
    SELECT data_oddania INTO ostatnie
    FROM oddania_krwi
    WHERE id_dawcy = NEW.id_dawcy
    ORDER BY data_oddania DESC
    LIMIT 1;

    IF ostatnie IS NOT NULL AND NEW.data_oddania < ostatnie + INTERVAL '56 days' THEN
        RAISE EXCEPTION 'Możesz oddać krew dopiero po %', ostatnie + INTERVAL '56 days';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_blokuj_wczesne_oddanie
BEFORE INSERT ON oddania_krwi
FOR EACH ROW
EXECUTE FUNCTION blokuj_wczesne_oddanie();


-- 1. Funkcja, która znajdzie ID dawcy i ID szpitala, a potem wpisze je do tabeli historii
CREATE OR REPLACE FUNCTION automatyczny_dawca_szpital()
RETURNS trigger AS $$
DECLARE
    v_id_dawcy INT;
    v_id_szpitala INT;
BEGIN
    -- Pobieramy ID dawcy na podstawie oddania
    SELECT id_dawcy INTO v_id_dawcy 
    FROM oddania_krwi 
    WHERE id_oddania = NEW.id_oddania;

    -- Pobieramy ID szpitala na podstawie zapotrzebowania
    SELECT id_szpitala INTO v_id_szpitala 
    FROM zapotrzebowania 
    WHERE id_zapotrzebowania = NEW.id_zapotrzebowania;

    -- Wstawiamy rekord do tabeli Dawca_Szpital
    -- (Używamy ON CONFLICT DO NOTHING, żeby nie wywaliło błędu, jak już coś tam jest)
    INSERT INTO Dawca_Szpital (id_dawcy, id_szpitala, id_oddania, data_przekazania)
    VALUES (v_id_dawcy, v_id_szpitala, NEW.id_oddania, CURRENT_DATE)
    ON CONFLICT DO NOTHING;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_dawca_szpital
AFTER INSERT ON Oddanie_Zapotrzebowanie
FOR EACH ROW
EXECUTE FUNCTION automatyczny_dawca_szpital();

-- ==========================================
-- DODATKOWE DANE TESTOWE (ROZSZERZENIE)
-- ==========================================

-- 1. Nowi Użytkownicy (3 dawców, 1 szpital, 1 pracownik)
insert into Uzytkownicy (login, haslo, rola) values
('dawca3',    crypt('dawcapass3', gen_salt('bf')), 'DAWCA'),   -- B Rh+
('dawca4',    crypt('dawcapass4', gen_salt('bf')), 'DAWCA'),   -- AB Rh- (rzadka)
('dawca5',    crypt('dawcapass5', gen_salt('bf')), 'DAWCA'),   -- 0 Rh+ (zakażony - test triggera)
('szpital2',  crypt('szpitpass2', gen_salt('bf')), 'SZPITAL'), -- Szpital Żeromskiego
('pracownik3',crypt('pracpass3',  gen_salt('bf')), 'PRACOWNIK'); -- Nowy laborant

-- 2. Profile Dawców
insert into Dawcy (imie, nazwisko, pesel, grupa_krwi, rh, kontakt, id_uzytkownika) values
('Tomasz', 'Zieliński', '85021411223', 'B',  '+', '500600700',
 (select id_uzytkownika from Uzytkownicy where login='dawca3')),
('Ewa',    'Wiśniewska','99032055443', 'AB', '-', '600700800',
 (select id_uzytkownika from Uzytkownicy where login='dawca4')),
('Kamil',  'Chory',     '95111122334', '0',  '+', '700800900',
 (select id_uzytkownika from Uzytkownicy where login='dawca5'));

-- 3. Profil Szpitala i Pracownika
insert into Szpitale (nazwa, adres, id_uzytkownika) values
('Szpital Specjalistyczny im. S. Żeromskiego', 'Kraków, os. Na Skarpie 66',
 (select id_uzytkownika from Uzytkownicy where login='szpital2'));

insert into Pracownicy_banku (imie, nazwisko, stanowisko, id_uzytkownika) values
('Adam', 'Nowy', 'laborant',
 (select id_uzytkownika from Uzytkownicy where login='pracownik3'));


-- 4. Zgłoszenia
insert into Zgloszenia (id_dawcy, data_zgloszenia, status) values
((select id_dawcy from Dawcy where pesel='85021411223'), '2025-12-08', 'zrealizowane'), -- Tomasz
((select id_dawcy from Dawcy where pesel='99032055443'), '2025-12-09', 'zrealizowane'), -- Ewa
((select id_dawcy from Dawcy where pesel='95111122334'), '2025-12-10', 'zrealizowane'); -- Kamil


-- 5. Oddania Krwi
-- Tomasz (B+) oddał krew
insert into Oddania_krwi (data_oddania, ilosc_ml, id_dawcy, id_zgloszenia, id_pracownika) values
('2025-12-09', 450,
 (select id_dawcy from Dawcy where pesel='85021411223'),
 (select id_zgloszenia from Zgloszenia where id_dawcy = (select id_dawcy from Dawcy where pesel='85021411223') limit 1),
 (select id_pracownika from Pracownicy_banku where nazwisko='Lekarz'));

-- Ewa (AB-) oddała krew (rzadka grupa)
insert into Oddania_krwi (data_oddania, ilosc_ml, id_dawcy, id_zgloszenia, id_pracownika) values
('2025-12-10', 450,
 (select id_dawcy from Dawcy where pesel='99032055443'),
 (select id_zgloszenia from Zgloszenia where id_dawcy = (select id_dawcy from Dawcy where pesel='99032055443') limit 1),
 (select id_pracownika from Pracownicy_banku where nazwisko='Lekarz'));

-- Kamil (0+) oddał krew (będzie oznaczona jako zakażona po badaniu)
insert into Oddania_krwi (data_oddania, ilosc_ml, id_dawcy, id_zgloszenia, id_pracownika) values
('2025-12-11', 450,
 (select id_dawcy from Dawcy where pesel='95111122334'),
 (select id_zgloszenia from Zgloszenia where id_dawcy = (select id_dawcy from Dawcy where pesel='95111122334') limit 1),
 (select id_pracownika from Pracownicy_banku where nazwisko='Lekarz'));


-- 6. Badania
-- Badanie Kamila wychodzi POZYTYWNE (HCV) -> Trigger powinien zmienić status oddania na 'odrzucone_badanie'
insert into Badania (id_oddania, rodzaj_badania, wynik, data_badania, id_pracownika) values
((select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='95111122334') order by id_oddania desc limit 1),
 'HCV', 'pozytywny', '2025-12-12', -- !!! UWAGA: Pozytywny wynik
 (select id_pracownika from Pracownicy_banku where nazwisko='Nowy'));

-- Badanie Tomasza (negatywne - OK)
insert into Badania (id_oddania, rodzaj_badania, wynik, data_badania, id_pracownika) values
((select id_oddania from Oddania_krwi where id_dawcy = (select id_dawcy from Dawcy where pesel='85021411223') order by id_oddania desc limit 1),
 'HIV', 'negatywny', '2025-12-10',
 (select id_pracownika from Pracownicy_banku where nazwisko='Laborant'));


-- 7. Zapotrzebowania (Nowy szpital potrzebuje krwi B+)
insert into Zapotrzebowania (id_szpitala, grupa_krwi, rh, ilosc_ml, status) values
((select id_szpitala from Szpitale where nazwa like '%Żeromskiego%'), 'B', '+', 400, 'oczekujace');

-- 8. Aktualizacja ilości
-- Musimy upewnić się, że nowe oddania mają ilosc_pozostala
UPDATE oddania_krwi
SET ilosc_pozostala = ilosc_ml
WHERE ilosc_pozostala = 0 AND status = 'dostepne';


