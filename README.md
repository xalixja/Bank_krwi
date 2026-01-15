#Projekt: System Zarządzania Bankiem Krwi
#Autorka: Alicja Borek

Aplikacja webowa wspierająca procesy w Regionalnym Centrum Krwiodawstwa i Krwiolecznictwa. System umożliwia zarządzanie dawcami, zapasami krwi, badaniami oraz realizację zapotrzebowań szpitali.

Projekt zrealizowany w ramach przedmiotu Bazy Danych 1.

## Funkcjonalności

* **Panel Dawcy:** Rejestracja, podgląd historii oddań, planowanie wizyt(z ograniczeniami), wyniki badań.
* **Panel Pracownika:** Rejestracja donacji, wprowadzanie wyników badań, zarządzanie magazynem krwi, realizacja zapotrzebowań.
* **Panel Szpitala:** Składanie zapotrzebowań na krew, podgląd statusu zamówień.
* **Panel Administratora:** Zarządzanie użytkownikami i uprawnieniami.
* **Logika biznesowa:** Automatyczne blokady (np. po pozytywnym wyniku badania), obliczanie terminów kolejnych oddań, algorytm FIFO przy wydawaniu krwi.

## Technologie

* **Backend:** Python 3.13, Flask
* **Baza danych:** PostgreSQL 14+
* **Frontend:** HTML5, Bootstrap 5, Jinja2
* **Biblioteki:** `psycopg2-binary` (sterownik DB), `Werkzeug` (bezpieczeństwo)

## Instrukcja uruchomienia

Aby uruchomić projekt na lokalnej maszynie, wykonaj poniższe kroki.

### 1. Wymagania wstępne
Upewnij się, że masz zainstalowane:
* Python (wersja 3.8 lub nowsza)
* PostgreSQL (wersja 14 lub nowsza)
* Git

### 2. Klonowanie repozytorium
```bash
git clone [https://github.com/xalixja/Bank_krwi.git](https://github.com/xalixja/Bank_krwi.git)
cd Bank_krwi
```

### 3. Konfiguracja środowiska wirtualnego
Zaleca się utworzenie wirtualnego środowiska, aby odizolować biblioteki projektu.
Windows:
```bash
python -m venv venv
.\venv\Scripts\activate
```
macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalacja zależności
```bash
pip install -r requirements.txt
```

### 5. Konfiguracja bazy danych (PostgreSQL)
-Upewnij się, że serwer PostgreSQL działa.
-Otwórz plik db/connection.py i sprawdź parametry połączenia. Domyślna konfiguracja w projekcie:
  Host: localhost
  Port: 5432
  Użytkownik: postgres
  Hasło: 123qwe (Zmień na swoje hasło do lokalnej bazy!)
  Baza: postgres
-Uruchom skrypt inicjalizujący bazę danych. Możesz to zrobić w pgAdmin, DBeaver lub z linii komend:
```bash
psql -U postgres -d postgres -f bank_krwi.sql
```
Skrypt ten utworzy schemat bank_krwi, tabele, triggery, widoki oraz zasili bazę danymi testowymi.

### 6. Uruchomienie aplikacji
Będąc w głównym katalogu projektu (i mając aktywne środowisko wirtualne), uruchom:
```bash
python app.py
```
Aplikacja powinna być dostępna pod adresem: http://127.0.0.1:5000

# Konta testowe
Baza danych została zasilona przykładowymi użytkownikami. Możesz użyć ich do przetestowania systemu:
Rola           Login      Hasło
Administrator  admin1     adminpass
Pracownik      pracownik1 pracpass
Szpital        szpital1   szpitpass
Dawca          dawca1     dawcapass

# Struktura projektu
app.py - Główny plik aplikacji (Flask).
db/ - Pliki konfiguracyjne bazy danych.
templates/ - Szablony HTML (widoki).
static/ - Plik CSS.
bank_krwi.sql - Skrypt SQL tworzący strukturę bazy.

