#!/usr/bin/env python3
"""
Generate Hungary NAT Curriculum Test Modules - One per subject per grade.
Based on actual Hungarian National Core Curriculum (NAT) 2020.
Each module = 45-minute test for ONE subject in ONE grade.
"""

import json
import os
import hashlib
from datetime import datetime, UTC
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parents[1] / "plans" / "test-modules" / "modules" / "hungary"

# Hungary NAT Curriculum - Subjects by Grade
# Based on official curriculum from oktatas.hu
HUNGARY_CURRICULUM = {
    # Grades 1-4 (Lower Primary)
    "grade-01": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Betűk és hangok", "Olvasás alapok", "Írás alapok", "Szövegértés"], "hours_per_week": 5},
        "math": {"name": "Matematika", "topics": ["Számolás 10-ig", "Számlálás", "Összeadás/Kivonás", "Térbeli orientáció"], "hours_per_week": 4},
        "ethics": {"name": "Etika", "topics": ["Értékek", "Szabályok", "Tisztelet", "Segítségnyújtás"], "hours_per_week": 1},
        "pe": {"name": "Testnevelés", "topics": ["Alapmozdulatok", "Játékok", "Egészség"], "hours_per_week": 5},
        "music": {"name": "Ének-zene", "topics": ["Dalok", "Ritmus", "Hangok"], "hours_per_week": 1},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Rajzolás", "Formák", "Színek"], "hours_per_week": 1},
        "technology": {"name": "Technika és tervezés", "topics": ["Anyagok", "Egyszerű eszközök", "Készítés"], "hours_per_week": 1},
    },
    "grade-02": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Olvasás fejlesztése", "Helyesírás", "Szövegértés", "Versek"], "hours_per_week": 5},
        "math": {"name": "Matematika", "topics": ["Számolás 100-ig", "Szorzás/Osztás alapok", "Mértekegységek", "Adatkezelés"], "hours_per_week": 4},
        "ethics": {"name": "Etika", "topics": ["Közösség", "Felelősség", "Család", "Iskola"], "hours_per_week": 1},
        "pe": {"name": "Testnevelés", "topics": ["Kondíció", "Játékok", "Egészség"], "hours_per_week": 5},
        "music": {"name": "Ének-zene", "topics": ["Dalok", "Ritmus", "Hangok", "Zenehangszer"], "hours_per_week": 1},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Rajzolás", "Festés", "Formák"], "hours_per_week": 1},
        "technology": {"name": "Technika és tervezés", "topics": ["Anyagok", "Eszközök", "Tervezés"], "hours_per_week": 1},
    },
    "grade-03": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Folyamatos olvasás", "Szövegértés", "Íráskészség", "Nyelvtan alapok"], "hours_per_week": 5},
        "math": {"name": "Matematika", "topics": ["Számolás 1000-ig", "Törtök alapok", "Geometria", "Adatkezelés"], "hours_per_week": 4},
        "ethics": {"name": "Etika", "topics": ["Önismeret", "Empátia", "Döntéshozatal", "Értékek"], "hours_per_week": 1},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 5},
        "music": {"name": "Ének-zene", "topics": ["Dalok", "Zeneelmélet", "Hangok"], "hours_per_week": 1},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Rajzolás", "Térkép", "Formák"], "hours_per_week": 1},
        "technology": {"name": "Technika és tervezés", "topics": ["Anyagok", "Eszközök", "Tervezés"], "hours_per_week": 1},
        "environment": {"name": "Környezetismeret", "topics": ["Természet", "Élővilág", "Környezetvédelem", "Földrajz alapok"], "hours_per_week": 2},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Számítógép alapok", "Biztonság", "Keresés"], "hours_per_week": 1},
    },
    "grade-04": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Komplex szövegértés", "Kreatív írás", "Nyelvtan", "Irodalom"], "hours_per_week": 5},
        "math": {"name": "Matematika", "topics": ["Számolás 10000-ig", "Tizedestörtök", "Mértékek", "Valószínűség"], "hours_per_week": 4},
        "ethics": {"name": "Etika", "topics": ["Demokrácia", "Jogok", "Tolerancia", "Felelősség"], "hours_per_week": 1},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 5},
        "music": {"name": "Ének-zene", "topics": ["Dalok", "Zeneelmélet", "Előadás"], "hours_per_week": 1},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Rajzolás", "Grafika", "Formák"], "hours_per_week": 1},
        "technology": {"name": "Technika és tervezés", "topics": ["Anyagok", "Eszközök", "Tervezés"], "hours_per_week": 1},
        "environment": {"name": "Környezetismeret", "topics": ["Természet", "Energia", "Földrajz", "Környezetvédelem"], "hours_per_week": 2},
        "foreign_language": {"name": "Élő idegen nyelv", "topics": ["Alap szókincs", "Egyszerű mondatok", "Kulturális ismeretek"], "hours_per_week": 2},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Programozás alapok", "Adatok", "Biztonság"], "hours_per_week": 1},
    },
    # Grades 5-8 (Upper Primary)
    "grade-05": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Irodalom", "Nyelvtan", "Érvelés", "Kommunikáció"], "hours_per_week": 4},
        "math": {"name": "Matematika", "topics": ["Racionális számok", "Törtök", "Százalék", "Algebra alapok"], "hours_per_week": 4},
        "history": {"name": "Történelem", "topics": ["Őskor", "Ókor", "Középkor kezdete", "Források"], "hours_per_week": 2},
        "ethics": {"name": "Etika", "topics": ["Identitás", "Társadalom", "Etikai dilemmák", "Döntéshozatal"], "hours_per_week": 1},
        "homeland": {"name": "Hon- és népismeret", "topics": ["Magyarország", "Tájak", "Népesség", "Gazdaság"], "hours_per_week": 2},
        "science": {"name": "Természettudomány", "topics": ["Energia", "Erő", "Anyagok", "Élővilág"], "hours_per_week": 3},
        "foreign_language": {"name": "Élő idegen nyelv", "topics": ["Nyelvtan", "Szókincs", "Kommunikáció", "Kultúra"], "hours_per_week": 3},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 4},
        "music": {"name": "Ének-zene", "topics": ["Dalok", "Zeneelmélet", "Előadás"], "hours_per_week": 1},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Rajzolás", "Festés", "Formák"], "hours_per_week": 1},
        "drama": {"name": "Dráma és színház", "topics": ["Játék", "Előadás", "Kreativitás"], "hours_per_week": 1},
        "technology": {"name": "Technika és tervezés", "topics": ["Anyagok", "Eszközök", "Tervezés"], "hours_per_week": 1},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Programozás", "Adatok", "Biztonság"], "hours_per_week": 1},
        "community": {"name": "Közösségi nevelés", "topics": ["Osztály", "Kooperáció", "Felelősség"], "hours_per_week": 1},
    },
    "grade-06": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Irodalomtörténet", "Nyelvtan", "Szakmai kommunikáció", "Érvelés"], "hours_per_week": 4},
        "math": {"name": "Matematika", "topics": ["Valós számok", "Gyökök", "Háromszögek", "Koordinátarendszer"], "hours_per_week": 4},
        "history": {"name": "Történelem", "topics": ["Középkor", "Újkor kezdete", "Magyarország", "Forráskritika"], "hours_per_week": 2},
        "ethics": {"name": "Etika", "topics": ["Emberi jogok", "Nemzetközi jogok", "Aktív állampolgárság", "Felelősség"], "hours_per_week": 1},
        "homeland": {"name": "Hon- és népismeret", "topics": ["Európa", "Világ", "Környezet", "Fenntarthatóság"], "hours_per_week": 2},
        "science": {"name": "Természettudomány", "topics": ["Anyag", "Kémia alapok", "Reakciók", "Anyagok keringése"], "hours_per_week": 3},
        "foreign_language": {"name": "Élő idegen nyelv", "topics": ["Nyelvtan", "Olvasás", "Írás", "Beszéd"], "hours_per_week": 3},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 4},
        "music": {"name": "Ének-zene", "topics": ["Dalok", "Zeneelmélet", "Előadás"], "hours_per_week": 1},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Rajzolás", "Grafika", "Formák"], "hours_per_week": 1},
        "drama": {"name": "Dráma és színház", "topics": ["Játék", "Előadás", "Kreativitás"], "hours_per_week": 1},
        "technology": {"name": "Technika és tervezés", "topics": ["Anyagok", "Eszközök", "Tervezés"], "hours_per_week": 1},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Algoritmusok", "Adatbázisok", "Biztonság"], "hours_per_week": 1},
        "community": {"name": "Közösségi nevelés", "topics": ["Csoport", "Vezetés", "Konfliktuskezelés"], "hours_per_week": 1},
    },
    "grade-07": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Klasszikus irodalom", "Stílusgyakorlat", "Érvelés", "Kommunikáció"], "hours_per_week": 4},
        "math": {"name": "Matematika", "topics": ["Egyenletek", "Síkidomok", "Függvények", "Statisztika"], "hours_per_week": 4},
        "history": {"name": "Történelem", "topics": ["Középkor", "Felfedezések", "Vallási háborúk", "Abszolutizmus"], "hours_per_week": 2},
        "biology": {"name": "Biológia", "topics": ["Sejtbiológia", "Genetika", "Osztódás", "Öröklődés"], "hours_per_week": 2},
        "chemistry": {"name": "Kémia", "topics": ["Elemek", "Vegyületek", "Reakciók", "Kémia mindennapokban"], "hours_per_week": 2},
        "physics": {"name": "Fizika", "topics": ["Mozgás", "Erők", "Energia", "Newton-törvények"], "hours_per_week": 2},
        "geography": {"name": "Földrajz", "topics": ["Térképek", "Klíma", "Gazdaság", "Népesség"], "hours_per_week": 2},
        "civics": {"name": "Állampolgári ismeretek", "topics": ["Alkotmány", "Jogállam", "EU", "Demokrácia"], "hours_per_week": 1},
        "foreign_language": {"name": "Élő idegen nyelv", "topics": ["Nyelvtan", "Olvasás", "Írás", "Beszéd B1"], "hours_per_week": 3},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 4},
        "music": {"name": "Ének-zene", "topics": ["Dalok", "Zeneelmélet", "Előadás"], "hours_per_week": 1},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Rajzolás", "Festés", "Formák"], "hours_per_week": 1},
        "drama": {"name": "Dráma és színház", "topics": ["Játék", "Előadás", "Kreativitás"], "hours_per_week": 1},
        "technology": {"name": "Technika és tervezés", "topics": ["Anyagok", "Eszközök", "Tervezés"], "hours_per_week": 1},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Informatika", "Programozás", "Adatbiztonság", "Etika"], "hours_per_week": 1},
        "community": {"name": "Közösségi nevelés", "topics": ["Osztály", "Kooperáció", "Felelősség"], "hours_per_week": 1},
    },
    "grade-08": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Modern irodalom", "Szakmai kommunikáció", "Életrajz", "Érvelés"], "hours_per_week": 4},
        "math": {"name": "Matematika", "topics": ["Lineáris függvények", "Valószínűség", "Statisztika", "Geometria"], "hours_per_week": 4},
        "history": {"name": "Történelem", "topics": ["19. század", "Ipari forradalom", "Nemzetállamok", "Kolonizáció"], "hours_per_week": 2},
        "biology": {"name": "Biológia", "topics": ["Emberi test", "Rendszerek", "Egészség", "Prevenció"], "hours_per_week": 2},
        "chemistry": {"name": "Kémia", "topics": ["Szerves kémia", "Élettani anyagok", "Környezetkémia", "Anyagok"], "hours_per_week": 2},
        "physics": {"name": "Fizika", "topics": ["Hőtan", "Hullámok", "Hang", "Fény", "Optika"], "hours_per_week": 2},
        "geography": {"name": "Földrajz", "topics": ["Európa", "Magyarország", "Tájak", "Gazdaság"], "hours_per_week": 2},
        "civics": {"name": "Állampolgári ismeretek", "topics": ["Demokrácia", "Piacgazdaság", "Szociális jogok", "Választások"], "hours_per_week": 1},
        "foreign_language": {"name": "Élő idegen nyelv", "topics": ["Nyelvtan B1", "Olvasás", "Írás", "Beszéd"], "hours_per_week": 3},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 4},
        "music": {"name": "Ének-zene", "topics": ["Dalok", "Zeneelmélet", "Előadás"], "hours_per_week": 1},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Rajzolás", "Grafika", "Formák"], "hours_per_week": 1},
        "drama": {"name": "Dráma és színház", "topics": ["Játék", "Előadás", "Kreativitás"], "hours_per_week": 1},
        "technology": {"name": "Technika és tervezés", "topics": ["Anyagok", "Eszközök", "Tervezés"], "hours_per_week": 1},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Programozás", "Adatbázisok", "Hálózatok", "Biztonság"], "hours_per_week": 1},
        "community": {"name": "Közösségi nevelés", "topics": ["Életút", "Karrier", "Döntéshozatal", "Felelősség"], "hours_per_week": 1},
    },
    # Grades 9-12 (Gimnazium)
    "grade-09": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Magyar irodalomtörténet", "Középkor", "Reneszánsz", "Barokk"], "hours_per_week": 4},
        "math": {"name": "Matematika", "topics": ["Függvények", "Polinomok", "Exponenciális", "Logaritmikus", "Határérték"], "hours_per_week": 4},
        "history": {"name": "Történelem", "topics": ["20. század", "Világháboruk", "Hidegháború", "Rendszerváltás"], "hours_per_week": 2},
        "biology": {"name": "Biológia", "topics": ["Molekuláris biológia", "DNS", "Fehérjék", "Géntechnológia"], "hours_per_week": 2},
        "chemistry": {"name": "Kémia", "topics": ["Ásványi kémia", "Periódusos rendszer", "Vázlatkötés", "Oldatok"], "hours_per_week": 2},
        "physics": {"name": "Fizika", "topics": ["Elektromágnesesség", "Elektrostatikus", "Áramkörök", "Mágneses mező"], "hours_per_week": 2},
        "geography": {"name": "Földrajz", "topics": ["Világföldrajz", "Kontinensek", "Globális problémák", "Fenntarthatóság"], "hours_per_week": 2},
        "civics": {"name": "Állampolgári ismeretek", "topics": ["Nemzetközi kapcsolatok", "EU", "ENSZ", "Globális jog"], "hours_per_week": 1},
        "foreign_language_1": {"name": "Első idegen nyelv", "topics": ["Nyelvtan B2", "Akadémiai írás", "Előadás", "Kultúra"], "hours_per_week": 3},
        "foreign_language_2": {"name": "Második idegen nyelv", "topics": ["Nyelvtan A2/B1", "Kommunikáció", "Kultúra"], "hours_per_week": 2},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 3},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Művészet", "Stílusok", "Kreativitás"], "hours_per_week": 1},
        "music": {"name": "Ének-zene", "topics": ["Zeneelmélet", "Előadás", "Történelem"], "hours_per_week": 1},
        "drama": {"name": "Dráma és színház", "topics": ["Színház", "Előadás", "Kreativitás"], "hours_per_week": 1},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Programozás", "Hálózatok", "Mesterséges intelligencia", "Adatbiztonság"], "hours_per_week": 1},
        "community": {"name": "Közösségi nevelés", "topics": ["Osztály", "Projektek", "Felelősség"], "hours_per_week": 1},
    },
    "grade-10": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Összeállítás", "Érvelés", "Esszé", "Vita", "Kritikai gondolkodás"], "hours_per_week": 4},
        "math": {"name": "Matematika", "topics": ["Deriválás", "Integrálás", "Alkalmazások", "Analízis alapok"], "hours_per_week": 4},
        "history": {"name": "Történelem", "topics": ["Magyarország története", "Honfoglalás", "Korszakok", "Mai Magyarország"], "hours_per_week": 2},
        "biology": {"name": "Biológia", "topics": ["Sejtbiológia", "Sejtciklus", "Mendel-törvények", "Génterápia"], "hours_per_week": 2},
        "chemistry": {"name": "Kémia", "topics": ["Atomfelépítés", "Kvantummechanika", "Kötéselmélet", "Reakciókinetika"], "hours_per_week": 2},
        "physics": {"name": "Fizika", "topics": ["Mechanika", "Kinematika", "Dynamika", "Energia-megmaradás"], "hours_per_week": 2},
        "geography": {"name": "Földrajz", "topics": ["Társadalomföldrajz", "Urbanizáció", "Globalizáció", "Regionális különbségek"], "hours_per_week": 2},
        "civics": {"name": "Állampolgári ismeretek", "topics": ["Alkotmányjog", "Közhatalom", "Közigazgatás", "Alapvető jogok"], "hours_per_week": 1},
        "foreign_language_1": {"name": "Első idegen nyelv", "topics": ["Komplex nyelvtan", "Akadémiai írás", "Előadás", "C1 felkészülés"], "hours_per_week": 3},
        "foreign_language_2": {"name": "Második idegen nyelv", "topics": ["Nyelvtan B1/B2", "Kommunikáció", "Kultúra"], "hours_per_week": 2},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 3},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Művészet", "Modern stílusok", "Portfólió"], "hours_per_week": 1},
        "music": {"name": "Ének-zene", "topics": ["Zeneelmélet", "Előadás", "Történelem"], "hours_per_week": 1},
        "drama": {"name": "Dráma és színház", "topics": ["Színház", "Előadás", "Kreativitás"], "hours_per_week": 1},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Adatbázisok", "SQL", "Web", "HTML/CSS", "JavaScript"], "hours_per_week": 1},
        "community": {"name": "Közösségi nevelés", "topics": ["Projektek", "Vezetés", "Felelősség"], "hours_per_week": 1},
    },
    "grade-11": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Modern magyar irodalom", "20. század", "Mai irodalom", "Intertextualitás"], "hours_per_week": 4},
        "math": {"name": "Matematika", "topics": ["Valószínűség-számítás", "Kombinatorika", "Eloszlások", "Statisztikai következtetés"], "hours_per_week": 4},
        "history": {"name": "Történelem", "topics": ["Európa és világ", "Rendszerváltás", "EU", "Globális kihívások"], "hours_per_week": 2},
        "biology": {"name": "Biológia", "topics": ["Ökológia", "Populációk", "Rendszerek", "Evolúció"], "hours_per_week": 2},
        "chemistry": {"name": "Kémia", "topics": ["Fizikális kémia", "Termodinamika", "Elektrokémia", "Felületi jelenségek"], "hours_per_week": 2},
        "physics": {"name": "Fizika", "topics": ["Hullámok", "Optika", "Geometriai optika", "Fizikai optika"], "hours_per_week": 2},
        "geography": {"name": "Földrajz", "topics": ["Környezetföldrajz", "Katasztrófák", "Klimaváltozás", "Erőforrások"], "hours_per_week": 2},
        "civics": {"name": "Állampolgári ismeretek", "topics": ["Gazdaságjog", "Munkajog", "Vállalkozás", "Társadalombiztosítás"], "hours_per_week": 1},
        "foreign_language_1": {"name": "Első idegen nyelv", "topics": ["C1 szint", "Akadémiai kommunikáció", "Szakmai nyelv", "Érettségi felkészülés"], "hours_per_week": 3},
        "foreign_language_2": {"name": "Második idegen nyelv", "topics": ["B2 szint", "Kommunikáció", "Kultúra"], "hours_per_week": 2},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség"], "hours_per_week": 2},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Művészet", "Portfólió", "Érettségi felkészülés"], "hours_per_week": 1},
        "music": {"name": "Ének-zene", "topics": ["Zeneelmélet", "Előadás", "Történelem"], "hours_per_week": 1},
        "drama": {"name": "Dráma és színház", "topics": ["Színház", "Előadás", "Kreativitás"], "hours_per_week": 1},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Szoftverfejlesztés", "OOP", "Verziókezelés", "Tesztelés", "Agile"], "hours_per_week": 1},
        "community": {"name": "Közösségi nevelés", "topics": ["Projektek", "Karriertervezés", "Felelősség"], "hours_per_week": 1},
    },
    "grade-12": {
        "hungarian": {"name": "Magyar nyelv és irodalom", "topics": ["Érettségi felkészülés", "Olvasás", "Írás", "Szóbeli", "Irodalom"], "hours_per_week": 4},
        "math": {"name": "Matematika", "topics": ["Érettségi felkészülés", "Függvények", "Analízis", "Alkalmazott matematika"], "hours_per_week": 4},
        "history": {"name": "Történelem", "topics": ["Érettségi felkészülés", "Korszakok", "Forráskritika", "Érvelés"], "hours_per_week": 2},
        "biology": {"name": "Biológia", "topics": ["Emberi fiziólogia", "Immunológia", "Rendszerek", "Betegségek", "Érettségi"], "hours_per_week": 2},
        "chemistry": {"name": "Kémia", "topics": ["Analitikus kémia", "Szerves kémia", "Spektroszkópia", "Gyógyszerkémia", "Érettségi"], "hours_per_week": 2},
        "physics": {"name": "Fizika", "topics": ["Modern fizika", "Relativitás", "Kvantumfizika", "Részecskefizika", "Érettségi"], "hours_per_week": 2},
        "geography": {"name": "Földrajz", "topics": ["Érettségi felkészülés", "Térkép", "Statisztika", "Elemzés", "Globális kérdések"], "hours_per_week": 2},
        "civics": {"name": "Állampolgári ismeretek", "topics": ["Polológia", "Jog", "Rendszerek", "Jogalkotás", "Nemzetközi jog", "Érettségi"], "hours_per_week": 1},
        "foreign_language_1": {"name": "Első idegen nyelv", "topics": ["Érettségi felkészülés", "C1/C2", "Szakmai nyelv", "Kommunikáció"], "hours_per_week": 3},
        "foreign_language_2": {"name": "Második idegen nyelv", "topics": ["Érettségi felkészülés", "B2", "Kommunikáció"], "hours_per_week": 2},
        "pe": {"name": "Testnevelés", "topics": ["Sportok", "Kondíció", "Egészség", "Életmód"], "hours_per_week": 2},
        "visual_arts": {"name": "Vizuális kultúra", "topics": ["Érettségi felkészülés", "Portfólió", "Művészet"], "hours_per_week": 1},
        "music": {"name": "Ének-zene", "topics": ["Zeneelmélet", "Előadás", "Történelem"], "hours_per_week": 1},
        "drama": {"name": "Dráma és színház", "topics": ["Színház", "Előadás", "Kreativitás"], "hours_per_week": 1},
        "digital_culture": {"name": "Digitális kultúra", "topics": ["Projektmunka", "DevOps", "Portfólió", "Karriertervezés", "Agile"], "hours_per_week": 1},
        "community": {"name": "Közösségi nevelés", "topics": ["Életút", "Döntéshozatal", "Felelősség", "Társadalmi részvétel"], "hours_per_week": 1},
    },
}

# Question type distribution per subject
SUBJECT_QUESTION_TYPES = {
    "math": {"multiple_choice": 3, "dynamic_math": 4, "essay": 3},
    "physics": {"multiple_choice": 3, "dynamic_math": 3, "essay": 4},
    "chemistry": {"multiple_choice": 4, "dynamic_math": 2, "essay": 4},
    "biology": {"multiple_choice": 4, "essay": 6},
    "hungarian": {"multiple_choice": 4, "essay": 6},
    "history": {"multiple_choice": 4, "essay": 6},
    "geography": {"multiple_choice": 4, "essay": 6},
    "civics": {"multiple_choice": 4, "essay": 6},
    "foreign_language_1": {"multiple_choice": 5, "essay": 5},
    "foreign_language_2": {"multiple_choice": 5, "essay": 5},
    "environment": {"multiple_choice": 4, "essay": 6},
    "science": {"multiple_choice": 4, "essay": 6},
    "homeland": {"multiple_choice": 4, "essay": 6},
    "ethics": {"multiple_choice": 3, "essay": 7},
    "digital_culture": {"multiple_choice": 4, "dynamic_math": 2, "essay": 4},
    "pe": {"multiple_choice": 5, "essay": 5},
    "music": {"multiple_choice": 5, "essay": 5},
    "visual_arts": {"multiple_choice": 5, "essay": 5},
    "drama": {"multiple_choice": 5, "essay": 5},
    "technology": {"multiple_choice": 4, "essay": 6},
    "community": {"multiple_choice": 3, "essay": 7},
    "music": {"multiple_choice": 5, "essay": 5},
}

def get_question_types(subject_key):
    """Get question type distribution for a subject."""
    return SUBJECT_QUESTION_TYPES.get(subject_key, {"multiple_choice": 5, "essay": 5})

def generate_questions(subject_key, subject_name, topics, grade_num, grade_str):
    """Generate 10 questions for a module with appropriate types."""
    q_types = get_question_types(subject_key)
    questions = []
    q_id = 1
    
    # Multiple choice questions
    for i in range(q_types.get("multiple_choice", 5)):
        topic = topics[i % len(topics)]
        questions.append({
            "id": f"q-{q_id:03d}",
            "question_type": "multiple_choice",
            "text": f"[{subject_name}] {topic}: Válassza a helyes választ.",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "rubric": None,
            "points": 5,
            "variables": [],
            "tags": [subject_key.lower(), topic.lower().replace(" ", "-")],
            "difficulty": "medium" if grade_num >= 7 else "easy",
            "estimated_time_minutes": 3,
            "curriculum_topic": f"HU-{grade_str}-{subject_key.upper()[:4]}-{topic[:20]}",
            "learning_objective": topic,
        })
        q_id += 1
    
    # Dynamic math questions (for math, physics, chemistry, digital_culture)
    for i in range(q_types.get("dynamic_math", 0)):
        topic = topics[(i + 3) % len(topics)]
        questions.append({
            "id": f"q-{q_id:03d}",
            "question_type": "dynamic_math",
            "text": f"[{subject_name}] {topic}: Számítsa ki az értéket. [rand:1-10]",
            "options": None,
            "correct_answer": "Változó alapú számítás",
            "rubric": "Pontszámítás: helyes képlet (2p), helyes helyettesítés (2p), helyes eredmény (1p)",
            "points": 5,
            "variables": [{"name": "x", "min": 1, "max": 10}, {"name": "y", "min": 1, "max": 10}],
            "tags": [subject_key.lower(), topic.lower().replace(" ", "-"), "randomized"],
            "difficulty": "medium" if grade_num >= 7 else "easy",
            "estimated_time_minutes": 5,
            "curriculum_topic": f"HU-{grade_str}-{subject_key.upper()[:4]}-{topic[:20]}",
            "learning_objective": topic,
        })
        q_id += 1
    
    # Essay questions
    for i in range(q_types.get("essay", 5)):
        topic = topics[(i + 5) % len(topics)]
        questions.append({
            "id": f"q-{q_id:03d}",
            "question_type": "essay",
            "text": f"[{subject_name}] {topic}: Írjon esszét/választ a témában.",
            "options": None,
            "correct_answer": "Minta válasz: részletes elmagyarázás a témával kapcsolatban.",
            "rubric": "Pontszámítás: tartalmi helyesség (4p), logikus felépítés (3p), nyelvi helyesség (2p), saját gondolat (1p). Teljes pontszám: 10.",
            "points": 10,
            "variables": [],
            "tags": [subject_key.lower(), topic.lower().replace(" ", "-"), "essay"],
            "difficulty": "hard" if grade_num >= 9 else "medium",
            "estimated_time_minutes": 8,
            "curriculum_topic": f"HU-{grade_str}-{subject_key.upper()[:4]}-{topic[:20]}",
            "learning_objective": topic,
        })
        q_id += 1
    
    return questions

def create_module(grade_str, subject_key, subject_data, grade_num):
    """Create a complete module JSON."""
    subject_name = subject_data["name"]
    topics = subject_data["topics"]
    
    module_id = f"{grade_str}-{subject_key}-{subject_name.lower().replace(' ', '-').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ö','o').replace('ő','o').replace('ú','u').replace('ü','u').replace('ű','u')}-1.0.0"
    module_id = module_id[:80]
    
    now = datetime.now(UTC).isoformat()
    
    questions = generate_questions(subject_key, subject_name, topics, grade_num, grade_str.replace('grade-', ''))
    total_points = sum(q["points"] for q in questions)
    
    # Determine if randomizer should be enabled
    randomizer_subjects = ["math", "physics", "chemistry", "digital_culture"]
    randomizer_enabled = subject_key in randomizer_subjects
    
    module = {
        "metadata": {
            "id": module_id,
            "name": f"{subject_name} - {grade_str.replace('grade-', 'Grade ').title()}",
            "version": "1.0.0",
            "description": f"45-minute test on {subject_name.lower()} for {grade_str.replace('grade-', 'Grade ')} students. Topics: {', '.join(topics)}.",
            "author": "PlannedEducation Curriculum Team",
            "author_id": "system",
            "created_at": now,
            "updated_at": now,
            "tags": [subject_key.lower()] + [t.lower().replace(" ", "-") for t in topics] + [grade_str],
            "subject": subject_key.lower(),
            "grade_level": grade_str,
            "license": "CC-BY-4.0",
            "checksum": "",
            "curriculum": "hungary-nat",
            "duration_minutes": 45,
            "total_points": total_points,
            "question_count": len(questions),
            "randomizer_enabled": randomizer_enabled,
            "difficulty": "hard" if grade_num >= 9 else ("medium" if grade_num >= 7 else "easy"),
            "prerequisites": [],
            "learning_objectives": topics,
        },
        "exam": {
            "title": f"{grade_str.replace('grade-', 'Grade ').title()} {subject_name}",
            "description": f"Test on {subject_name.lower()} covering: {', '.join(topics).lower()}",
            "duration_minutes": 45,
            "instructions": "Answer all questions. You have 45 minutes. Show your work for calculations.",
            "settings": {
                "shuffle_questions": True,
                "shuffle_options": True,
                "show_results_immediately": False,
                "allow_review": True,
                "require_seb": False,
                "time_multiplier": 1.0,
                "passing_score": 60,
                "delivery_mode": "classroom",
                "allow_digital_hand_raise": False,
                "randomizer_enabled": randomizer_enabled,
                "randomizer_seed": None,
            },
        },
        "questions": questions,
        "rubrics": [],
    }
    
    # Calculate checksum
    pkg_copy = module.copy()
    pkg_copy["metadata"] = pkg_copy["metadata"].copy()
    pkg_copy["metadata"]["checksum"] = ""
    content = json.dumps(pkg_copy, sort_keys=True, separators=(',', ':'))
    module["metadata"]["checksum"] = hashlib.sha256(content.encode()).hexdigest()
    
    return module

def main():
    print("Generating Hungary NAT Curriculum Test Modules (one per subject per grade)...")
    
    total_modules = 0
    for grade_str, subjects in HUNGARY_CURRICULUM.items():
        grade_num = int(grade_str.split("-")[1])
        grade_path = BASE_PATH / grade_str
        
        for subject_key, subject_data in subjects.items():
            subject_path = grade_path / subject_key.lower()
            subject_path.mkdir(parents=True, exist_ok=True)
            
            module = create_module(grade_str, subject_key, subject_data, grade_num)
            
            # Create filename
            subject_name = subject_data["name"]
            safe_name = subject_name.lower().replace(" ", "-").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ö","o").replace("ő","o").replace("ú","u").replace("ü","u").replace("ű","u")
            filename = f"module-01-{safe_name}.json"
            filepath = subject_path / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(module, f, indent=2, ensure_ascii=False)
            
            print(f"  Created: {grade_str}/{subject_key}/{filename} ({len(module['questions'])} questions, {module['metadata']['total_points']} pts)")
            total_modules += 1
    
    print(f"\nTotal modules created: {total_modules}")
    print("Done!")

if __name__ == "__main__":
    main()