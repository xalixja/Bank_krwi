-- włącz rozszerzenie pgcrypto
create extension if not exists pgcrypto;

-- utworzenie schematu
create schema if not exists bank_krwi;
set search_path to bank_krwi;

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
    kontakt varchar(15),
    id_uzytkownika int references Uzytkownicy(id_uzytkownika)
);

create table Pracownicy_banku (
    id_pracownika serial primary key,
    imie varchar(30) not null,
    nazwisko varchar(30) not null,
    stanowisko varchar(20) check (stanowisko in ('lekarz','laborant','administrator')),
    id_uzytkownika int references Uzytkownicy(id_uzytkownika)
);

create table Szpitale (
    id_szpitala serial primary key,
    nazwa varchar(100) not null,
    adres varchar(200),
    id_uzytkownika int references Uzytkownicy(id_uzytkownika)
);

create table Zgloszenia (
    id_zgloszenia serial primary key,
    id_dawcy int references Dawcy(id_dawcy),
    data_zgloszenia date default current_date,
    status varchar(20) check (status in ('oczekujace','zaakceptowane','odrzucone'))
);

create table Oddania_krwi (
    id_oddania serial primary key,
    data_oddania date not null,
    ilosc_ml int check (ilosc_ml between 200 and 500),
    id_dawcy int references Dawcy(id_dawcy),
    id_zgloszenia int references Zgloszenia(id_zgloszenia),
    id_pracownika int references Pracownicy_banku(id_pracownika)
);

create table Badania (
    id_badania serial primary key,
    id_oddania int references Oddania_krwi(id_oddania),
    rodzaj_badania varchar(50) not null,
    wynik varchar(50),
    data_badania date,
    id_pracownika int references Pracownicy_banku(id_pracownika)
);

create table Magazyn (
    id_magazynu serial primary key,
    grupa_krwi varchar(2) check (grupa_krwi in ('A','B','AB','0')),
    rh varchar(1) check (rh in ('+','-')),
    ilosc_ml int check (ilosc_ml > 0),
    data_waznosci date,
    id_oddania int references Oddania_krwi(id_oddania)
);

create table Zapotrzebowania (
    id_zapotrzebowania serial primary key,
    id_szpitala int references Szpitale(id_szpitala),
    grupa_krwi varchar(2) check (grupa_krwi in ('A','B','AB','0')),
    rh varchar(1) check (rh in ('+','-')),
    ilosc_ml int check (ilosc_ml > 0),
    status varchar(20) check (status in ('oczekujace','zrealizowane'))
);

create table Wydania (
    id_wydania serial primary key,
    id_zapotrzebowania int references Zapotrzebowania(id_zapotrzebowania),
    data_wydania date default current_date,
    ilosc_ml int check (ilosc_ml > 0),
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

insert into Uzytkownicy (login, haslo, rola) values
('admin1', crypt('adminpass', gen_salt('bf')), 'ADMIN'),
('pracownik1', crypt('pracpass', gen_salt('bf')), 'PRACOWNIK'),
('pracownik2', crypt('pracpass2', gen_salt('bf')), 'PRACOWNIK'),
('szpital1', crypt('szpitpass', gen_salt('bf')), 'SZPITAL'),
('dawca1', crypt('dawcapass', gen_salt('bf')), 'DAWCA'),
('dawca2', crypt('dawcapass2', gen_salt('bf')), 'DAWCA');

insert into Dawcy (imie, nazwisko, pesel, grupa_krwi, rh, kontakt, id_uzytkownika) values
('Jan', 'Kowalski', '90010112345', 'A', '+', '123456789', 5),
('Anna', 'Nowak', '92050567890', '0', '-', '987654321', 6);

insert into Pracownicy_banku (imie, nazwisko, stanowisko, id_uzytkownika) values
('Piotr', 'Lekarz', 'lekarz', 2),
('Maria', 'Laborant', 'laborant', 3);

insert into Szpitale (nazwa, adres, id_uzytkownika) values
('Szpital Uniwersytecki', 'Kraków, ul. Kopernika 36', 4);

insert into Zgloszenia (id_dawcy, data_zgloszenia, status) values
(1, '2025-12-01', 'zaakceptowane'),
(2, '2025-12-02', 'oczekujace');

insert into Oddania_krwi (data_oddania, ilosc_ml, id_dawcy, id_zgloszenia, id_pracownika) values
('2025-12-03', 450, 1, 1, 1),
('2025-12-04', 500, 2, 2, 2);

insert into Badania (id_oddania, rodzaj_badania, wynik, data_badania, id_pracownika) values
(1, 'HIV', 'negatywny', '2025-12-05', 1),
(1, 'HBV', 'negatywny', '2025-12-05', 2),
(2, 'HCV', 'negatywny', '2025-12-06', 2);

insert into Magazyn (grupa_krwi, rh, ilosc_ml, data_waznosci, id_oddania) values
('A', '+', 450, '2026-01-14', 1),
('0', '-', 500, '2026-01-15', 2);

insert into Zapotrzebowania (id_szpitala, grupa_krwi, rh, ilosc_ml, status) values
(1, 'A', '+', 300, 'oczekujace'),
(1, '0', '-', 500, 'zrealizowane');

insert into Wydania (id_zapotrzebowania, data_wydania, ilosc_ml, id_pracownika) values
(2, '2025-12-07', 500, 1);

insert into Oddanie_Zapotrzebowanie (id_oddania, id_zapotrzebowania, ilosc_ml) values
(1, 1, 300),
(2, 2, 500);

insert into Dawca_Szpital (id_dawcy, id_szpitala, id_oddania, data_przekazania) values
(1, 1, 1, '2025-12-07'),
(2, 1, 2, '2025-12-08');

--zapisywanie hasla
--insert into Uzytkownicy (login, haslo, rola, data_rejestracji)
--values ('jan_kowalski', crypt('tajnehaslo', gen_salt('bf')), 'DAWCA', current_date);

--weryfikacja hasla
--select * from Uzytkownicy
--where login = 'jan_kowalski'
--and haslo = crypt('tajnehaslo', haslo);
