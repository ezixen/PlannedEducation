#!/usr/bin/env python3
"""
Curriculum Module Generator for All Countries
Creates Hungary-level depth modules for Canada, Germany, UK, USA, Australia, EU,
Finland, Netherlands, Sweden, Norway, Denmark, Switzerland, Austria, Belgium, Ireland, New Zealand
Following the PlannedEducation .pepkg format specification.
"""

import json
import uuid
import os
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_ROOT = os.path.join(REPO_ROOT, "plans", "test-modules", "modules")

# Country curriculum configurations with research sources
COUNTRY_CONFIGS = {
    "canada": {
        "curriculum": "canada-ontario",
        "country_name": "Canada",
        "curriculum_source": "Ontario Ministry of Education - Ontario Curriculum",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "germany": {
        "curriculum": "germany-bildungsplaene",
        "country_name": "Germany",
        "curriculum_source": "Germany - Bildungspläne (Curriculum Frameworks) by State",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "uk": {
        "curriculum": "uk-national",
        "country_name": "United Kingdom",
        "curriculum_source": "UK Department for Education - National Curriculum",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "usa": {
        "curriculum": "usa-common-core",
        "country_name": "USA",
        "curriculum_source": "USA - Common Core State Standards & NGSS",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "australia": {
        "curriculum": "australia-curriculum",
        "country_name": "Australia",
        "curriculum_source": "Australia - Australian Curriculum (ACARA)",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "eu": {
        "curriculum": "eu-key-competences",
        "country_name": "European Union",
        "curriculum_source": "EU - Key Competences for Lifelong Learning",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "finland": {
        "curriculum": "finland-national-core-curriculum-2016",
        "country_name": "Finland",
        "curriculum_source": "Finnish National Agency for Education (EDUFI) - National Core Curriculum for Basic Education 2016",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "netherlands": {
        "curriculum": "netherlands-slo-kerndoelen",
        "country_name": "Netherlands",
        "curriculum_source": "SLO Netherlands - Kerndoelen (Core Objectives) for Primary and Secondary Education",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "sweden": {
        "curriculum": "sweden-skolverket-laroplan",
        "country_name": "Sweden",
        "curriculum_source": "Skolverket - Swedish National Curriculum (Läroplan) for Compulsory School",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "norway": {
        "curriculum": "norway-udir-lareplanverket",
        "country_name": "Norway",
        "curriculum_source": "Norwegian Directorate for Education and Training (Udir) - Læreplanverket (Curriculum)",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "denmark": {
        "curriculum": "denmark-emu-faelles-maal",
        "country_name": "Denmark",
        "curriculum_source": "Danish Ministry of Education (EMU) - Fælles Mål (Common Objectives)",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "switzerland": {
        "curriculum": "switzerland-lehrplan-21",
        "country_name": "Switzerland",
        "curriculum_source": "Swiss Conference of Cantonal Ministers of Education (EDK) - Lehrplan 21",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "austria": {
        "curriculum": "austria-lehrplaene",
        "country_name": "Austria",
        "curriculum_source": "Austrian Federal Ministry of Education (BMBWF) - Lehrpläne (Curricula)",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "belgium": {
        "curriculum": "belgium-flemish-french-curricula",
        "country_name": "Belgium",
        "curriculum_source": "Belgium - Flemish Community (Vlaanderen) and French Community (FWB) Curricula",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "ireland": {
        "curriculum": "ireland-ncca-curriculum",
        "country_name": "Ireland",
        "curriculum_source": "Ireland - National Council for Curriculum and Assessment (NCCA) Curriculum",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "new_zealand": {
        "curriculum": "new-zealand-nzc-te-mataiaho",
        "country_name": "New Zealand",
        "curriculum_source": "New Zealand Ministry of Education - The New Zealand Curriculum | Te Mātaiaho (Tāhūrangi)",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    },
    "hungary": {
        "curriculum": "hungary-nat",
        "country_name": "Hungary",
        "curriculum_source": "Hungarian National Curriculum (NAT) - Oktatási Hivatal",
        "grades": {
            "grade-01": ["english", "math", "science"],
            "grade-02": ["math", "science"],
            "grade-03": ["math", "science"],
            "grade-04": ["english", "math", "science"],
            "grade-05": ["math", "science"],
            "grade-06": ["math", "science"],
            "grade-07": ["biology", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-08": ["biology", "chemistry", "civics", "english", "geography", "history", "math", "physics", "science"],
            "grade-09": ["civics", "english", "geography", "history", "math", "physics"],
            "grade-10": ["biology", "chemistry", "civics", "english", "history", "math", "physics"],
            "grade-11": ["biology", "civics", "history", "math", "physics"],
            "grade-12": ["biology", "civics", "geography", "history", "math"],
        }
    }
}

# Subject topic templates for each subject and grade level
SUBJECT_TOPICS = {
    "math": {
        "grade-01": [("Számlálás 10-ig", "Counting to 10", "easy", 3),
                     ("Összeadás 10-ig", "Addition to 10", "easy", 3),
                     ("Kivonás 10-ig", "Subtraction to 10", "easy", 3),
                     ("Számlálás 20-ig", "Counting to 20", "easy", 3),
                     ("Összeadás 20-ig", "Addition to 20", "easy", 3)],
        "grade-02": [("Számlálás 100-ig", "Counting to 100", "easy", 3),
                     ("Összeadás 100-ig", "Addition to 100", "easy", 3),
                     ("Kivonás 100-ig", "Subtraction to 100", "easy", 3),
                     ("Szorzás alapok", "Multiplication basics", "easy", 3),
                     ("Osztás alapok", "Division basics", "easy", 3)],
        "grade-03": [("Számlálás 1000-ig", "Counting to 1000", "easy", 3),
                     ("Összeadás 1000-ig", "Addition to 1000", "easy", 3),
                     ("Kivonás 1000-ig", "Subtraction to 1000", "easy", 3),
                     ("Szorzótábla", "Multiplication table", "easy", 3),
                     ("Osztástábla", "Division table", "easy", 3)],
        "grade-04": [("Tizedes számok", "Decimal numbers", "easy", 3),
                     ("Összeadás tizedes", "Decimal addition", "easy", 3),
                     ("Kivonás tizedes", "Decimal subtraction", "easy", 3),
                     ("Szorzás tizedes", "Decimal multiplication", "easy", 3),
                     ("Osztás tizedes", "Decimal division", "easy", 3)],
        "grade-05": [("Törtek alapok", "Fraction basics", "easy", 3),
                     ("Törtek összeadása", "Fraction addition", "easy", 3),
                     ("Törtek kivonása", "Fraction subtraction", "easy", 3),
                     ("Törtek szorzása", "Fraction multiplication", "easy", 3),
                     ("Törtek osztása", "Fraction division", "easy", 3)],
        "grade-06": [("Általános tört", "General fractions", "easy", 3),
                     ("Tört műveletek", "Fraction operations", "easy", 3),
                     ("Százalék alapok", "Percentage basics", "easy", 3),
                     ("Százalék számítás", "Percentage calculation", "easy", 3),
                     ("Aranyszerű arány", "Proportional ratio", "easy", 3)],
        "grade-07": [("Racionális számok", "Rational numbers", "easy", 3),
                     ("Algebrai kifejezések", "Algebraic expressions", "easy", 3),
                     ("Egyenletek", "Equations", "easy", 3),
                     ("Geometria alapok", "Geometry basics", "easy", 3),
                     ("Statisztika alapok", "Statistics basics", "easy", 3)],
        "grade-08": [("Valós számok", "Real numbers", "easy", 3),
                     ("Függvények", "Functions", "easy", 3),
                     ("Lineáris egyenletek", "Linear equations", "easy", 3),
                     ("Geometria", "Geometry", "easy", 3),
                     ("Statisztika", "Statistics", "easy", 3)],
        "grade-09": [("Függvények és határek", "Functions and limits", "easy", 3),
                     ("Deriválás", "Differentiation", "easy", 3),
                     ("Integrálás", "Integration", "easy", 3),
                     ("Valószínűség", "Probability", "easy", 3),
                     ("Statisztika", "Statistics", "easy", 3)],
        "grade-10": [("Függvények és statisztika", "Functions and statistics", "easy", 3),
                     ("Deriválás és integrálás", "Differentiation and integration", "easy", 3),
                     ("Valószínűség-számítás", "Probability calculation", "easy", 3),
                     ("Statisztikai elemzés", "Statistical analysis", "easy", 3),
                     ("Geometria", "Geometry", "easy", 3)],
        "grade-11": [("Függvények", "Functions", "easy", 3),
                     ("Deriválás", "Differentiation", "easy", 3),
                     ("Integrálás", "Integration", "easy", 3),
                     ("Valószínűség", "Probability", "easy", 3),
                     ("Statisztika", "Statistics", "easy", 3)],
        "grade-12": [("Deriválás és integrálás", "Differentiation and integration", "easy", 3),
                     ("Valószínűség-számítás", "Probability calculation", "easy", 3),
                     ("Statisztikai elemzés", "Statistical analysis", "easy", 3),
                     ("Geometria", "Geometry", "easy", 3),
                     ("Matematikai elemzés", "Mathematical analysis", "easy", 3)],
    },
    "physics": {
        "grade-07": [("Energia és erő", "Energy and force", "easy", 3),
                     ("Erők és mozgás", "Forces and motion", "easy", 3),
                     ("Mozgás", "Motion", "easy", 3),
                     ("Energia", "Energy", "easy", 3),
                     ("Erő", "Force", "easy", 3)],
        "grade-08": [("Mechanika alapok", "Mechanics basics", "easy", 3),
                     ("Erők", "Forces", "easy", 3),
                     ("Mozgás", "Motion", "easy", 3),
                     ("Energia", "Energy", "easy", 3),
                     ("Mű", "Work", "easy", 3)],
        "grade-09": [("Mechanika", "Mechanics", "easy", 3),
                     ("Erők és mozgás", "Forces and motion", "easy", 3),
                     ("Energia", "Energy", "easy", 3),
                     ("Hullamok", "Waves", "easy", 3),
                     ("Optika", "Optics", "easy", 3)],
        "grade-10": [("Mechanika", "Mechanics", "easy", 3),
                     ("Hullamok és optika", "Waves and optics", "easy", 3),
                     ("Elektromágnesesség", "Electromagnetism", "easy", 3),
                     ("Modern fizika", "Modern physics", "easy", 3),
                     ("Fizika felkészülés", "Physics preparation", "easy", 3)],
        "grade-11": [("Mechanika", "Mechanics", "easy", 3),
                     ("Hullamok", "Waves", "easy", 3),
                     ("Optika", "Optics", "easy", 3),
                     ("Elektromágnesesség", "Electromagnetism", "easy", 3),
                     ("Modern fizika", "Modern physics", "easy", 3)],
        "grade-12": [("Mechanika", "Mechanics", "easy", 3),
                     ("Hullamok és optika", "Waves and optics", "easy", 3),
                     ("Elektromágnesesség", "Electromagnetism", "easy", 3),
                     ("Modern fizika", "Modern physics", "easy", 3),
                     ("Fizika felkészülés", "Physics preparation", "easy", 3)],
    },
    "chemistry": {
        "grade-08": [("Anyagok és tulajdonságaik", "Substances and properties", "easy", 3),
                     ("Anyagváltozások", "Substance changes", "easy", 3),
                     ("Kémiai reakciók", "Chemical reactions", "easy", 3),
                     ("Savak és bazák", "Acids and bases", "easy", 3),
                     ("Kémiai egyenletek", "Chemical equations", "easy", 3)],
        "grade-10": [("Szerkezeti kémia", "Structural chemistry", "easy", 3),
                     ("Szerves kémia alapok", "Organic chemistry basics", "easy", 3),
                     ("Kémiai reakciók", "Chemical reactions", "easy", 3),
                     ("Savak és bazák", "Acids and bases", "easy", 3),
                     ("Kémiai egyenleg", "Chemical equilibrium", "easy", 3)],
        "grade-11": [("Szerkezeti kémia", "Structural chemistry", "easy", 3),
                     ("Szerves kémia", "Organic chemistry", "easy", 3),
                     ("Kémiai reakciók", "Chemical reactions", "easy", 3),
                     ("Savak és bazák", "Acids and bases", "easy", 3),
                     ("Kémiai egyenleg", "Chemical equilibrium", "easy", 3)],
    },
    "biology": {
        "grade-07": [("Sejtbiológia és genetika", "Cell biology and genetics", "easy", 3),
                     ("Sejt szerkezete", "Cell structure", "easy", 3),
                     ("Genetika alapok", "Genetics basics", "easy", 3),
                     ("Ökológia", "Ecology", "easy", 3),
                     ("Ökológiai rendszerek", "Ecological systems", "easy", 3)],
        "grade-08": [("Embri test és egészség", "Human body and health", "easy", 3),
                     ("Embri test szerkezete", "Human body structure", "easy", 3),
                     ("Észek", "Senses", "easy", 3),
                     ("Észlelés", "Perception", "easy", 3),
                     ("Egészség", "Health", "easy", 3)],
        "grade-10": [("Sejtbiológia és genetika", "Cell biology and genetics", "easy", 3),
                     ("Sejt szerkezete", "Cell structure", "easy", 3),
                     ("Genetika", "Genetics", "easy", 3),
                     ("Ökológia", "Ecology", "easy", 3),
                     ("Ökológiai rendszerek", "Ecological systems", "easy", 3)],
        "grade-11": [("Sejtbiológia és genetika", "Cell biology and genetics", "easy", 3),
                     ("Sejt szerkezete", "Cell structure", "easy", 3),
                     ("Genetika", "Genetics", "easy", 3),
                     ("Ökológia", "Ecology", "easy", 3),
                     ("Ökológiai rendszerek", "Ecological systems", "easy", 3)],
        "grade-12": [("Embri fiziologia és immunológia", "Human physiology and immunology", "easy", 3),
                     ("Embri test fiziológiája", "Human body physiology", "easy", 3),
                     ("Immunológia", "Immunology", "easy", 3),
                     ("Ökológia", "Ecology", "easy", 3),
                     ("Ökológiai rendszerek", "Ecological systems", "easy", 3)],
    },
    "english": {
        "grade-01": [("Phonics alapok", "Phonics basics", "easy", 3),
                     ("Angol szavak", "English words", "easy", 3),
                     ("Angol mondatok", "English sentences", "easy", 3),
                     ("Angol olvasás", "English reading", "easy", 3),
                     ("Angol írás", "English writing", "easy", 3)],
        "grade-04": [("Angol nyelv A2", "English language A2", "easy", 3),
                     ("Angol grammatika", "English grammar", "easy", 3),
                     ("Angol szókincs", "English vocabulary", "easy", 3),
                     ("Angol olvasás", "English reading", "easy", 3),
                     ("Angol írás", "English writing", "easy", 3)],
        "grade-07": [("Angol nyelv A2", "English language A2", "easy", 3),
                     ("Angol grammatika", "English grammar", "easy", 3),
                     ("Angol szókincs", "English vocabulary", "easy", 3),
                     ("Angol olvasás", "English reading", "easy", 3),
                     ("Angol írás", "English writing", "easy", 3)],
        "grade-08": [("Angol nyelv B1", "English language B1", "easy", 3),
                     ("Angol grammatika", "English grammar", "easy", 3),
                     ("Angol szókincs", "English vocabulary", "easy", 3),
                     ("Angol olvasás", "English reading", "easy", 3),
                     ("Angol írás", "English writing", "easy", 3)],
        "grade-09": [("Angol nyelv B1", "English language B1", "easy", 3),
                     ("Angol grammatika", "English grammar", "easy", 3),
                     ("Angol szókincs", "English vocabulary", "easy", 3),
                     ("Angol olvasás", "English reading", "easy", 3),
                     ("Angol írás", "English writing", "easy", 3)],
        "grade-10": [("Angol nyelv B2", "English language B2", "easy", 3),
                     ("Angol grammatika", "English grammar", "easy", 3),
                     ("Angol szókincs", "English vocabulary", "easy", 3),
                     ("Angol olvasás", "English reading", "easy", 3),
                     ("Angol írás", "English writing", "easy", 3)],
        "grade-11": [("Angol nyelv B2", "English language B2", "easy", 3),
                     ("Angol grammatika", "English grammar", "easy", 3),
                     ("Angol szókincs", "English vocabulary", "easy", 3),
                     ("Angol olvasás", "English reading", "easy", 3),
                     ("Angol írás", "English writing", "easy", 3)],
    },
    "science": {
        "grade-01": [("Természet és környezet", "Nature and environment", "easy", 3),
                     ("Növények és állatok", "Plants and animals", "easy", 3),
                     ("Természet", "Nature", "easy", 3),
                     ("Környezet", "Environment", "easy", 3),
                     ("Természetvédelem", "Nature conservation", "easy", 3)],
        "grade-02": [("Természet és környezet", "Nature and environment", "easy", 3),
                     ("Növények és állatok", "Plants and animals", "easy", 3),
                     ("Természet", "Nature", "easy", 3),
                     ("Környezet", "Environment", "easy", 3),
                     ("Természetvédelem", "Nature conservation", "easy", 3)],
        "grade-03": [("Természet és környezet", "Nature and environment", "easy", 3),
                     ("Növények és állatok", "Plants and animals", "easy", 3),
                     ("Természet", "Nature", "easy", 3),
                     ("Környezet", "Environment", "easy", 3),
                     ("Természetvédelem", "Nature conservation", "easy", 3)],
        "grade-04": [("Természet és környezet", "Nature and environment", "easy", 3),
                     ("Növények és állatok", "Plants and animals", "easy", 3),
                     ("Természet", "Nature", "easy", 3),
                     ("Környezet", "Environment", "easy", 3),
                     ("Természetvédelem", "Nature conservation", "easy", 3)],
        "grade-05": [("Természet és környezet", "Nature and environment", "easy", 3),
                     ("Növények és állatok", "Plants and animals", "easy", 3),
                     ("Természet", "Nature", "easy", 3),
                     ("Környezet", "Environment", "easy", 3),
                     ("Természetvédelem", "Nature conservation", "easy", 3)],
        "grade-06": [("Természet és környezet", "Nature and environment", "easy", 3),
                     ("Növények és állatok", "Plants and animals", "easy", 3),
                     ("Természet", "Nature", "easy", 3),
                     ("Környezet", "Environment", "easy", 3),
                     ("Természetvédelem", "Nature conservation", "easy", 3)],
        "grade-07": [("Természet és környezet", "Nature and environment", "easy", 3),
                     ("Növények és állatok", "Plants and animals", "easy", 3),
                     ("Természet", "Nature", "easy", 3),
                     ("Környezet", "Environment", "easy", 3),
                     ("Természetvédelem", "Nature conservation", "easy", 3)],
    },
    "civics": {
        "grade-07": [("Állam és jog", "State and law", "easy", 3),
                     ("Állam szerkezete", "State structure", "easy", 3),
                     ("Jog alapok", "Law basics", "easy", 3),
                     ("Polgári jog", "Civil law", "easy", 3),
                     ("Polgári jog", "Civil law", "easy", 3)],
        "grade-08": [("Állam és jog", "State and law", "easy", 3),
                     ("Állam szerkezete", "State structure", "easy", 3),
                     ("Jog alapok", "Law basics", "easy", 3),
                     ("Polgári jog", "Civil law", "easy", 3),
                     ("Polgári jog", "Civil law", "easy", 3)],
        "grade-09": [("Demokracia és piacgazdaság", "Democracy and market economy", "easy", 3),
                     ("Demokracia", "Democracy", "easy", 3),
                     ("Piacgazdaság", "Market economy", "easy", 3),
                     ("Polgári jog", "Civil law", "easy", 3),
                     ("Állam szerkezete", "State structure", "easy", 3)],
        "grade-10": [("Demokrácia és piacgazdaság", "Democracy and market economy", "easy", 3),
                     ("Demokrácia", "Democracy", "easy", 3),
                     ("Piacgazdaság", "Market economy", "easy", 3),
                     ("Polgári jog", "Civil law", "easy", 3),
                     ("Állam szerkezete", "State structure", "easy", 3)],
        "grade-11": [("Demokrácia és piacgazdaság", "Democracy and market economy", "easy", 3),
                     ("Demokrácia", "Democracy", "easy", 3),
                     ("Piacgazdaság", "Market economy", "easy", 3),
                     ("Polgári jog", "Civil law", "easy", 3),
                     ("Állam szerkezete", "State structure", "easy", 3)],
        "grade-12": [("Polológia és jog-erettségi", "Politology and law-maturity", "easy", 3),
                     ("Polológia", "Politology", "easy", 3),
                     ("Jog-erettségi", "Law-maturity", "easy", 3),
                     ("Polgári jog", "Civil law", "easy", 3),
                     ("Állam szerkezete", "State structure", "easy", 3)],
    },
    "history": {
        "grade-07": [("Középkor és kora újkor", "Middle Ages and early modern period", "easy", 3),
                     ("Középkor", "Middle Ages", "easy", 3),
                     ("Kora újkor", "Early modern period", "easy", 3),
                     ("Történelem", "History", "easy", 3),
                     ("Történelmi események", "Historical events", "easy", 3)],
        "grade-08": [("Újkor - 19. század", "Modern period - 19th century", "easy", 3),
                     ("Újkor", "Modern period", "easy", 3),
                     ("19. század", "19th century", "easy", 3),
                     ("Történelem", "History", "easy", 3),
                     ("Történelmi események", "Historical events", "easy", 3)],
        "grade-09": [("20. század története", "History of the 20th century", "easy", 3),
                     ("20. század", "20th century", "easy", 3),
                     ("Történelem", "History", "easy", 3),
                     ("Történelmi események", "Historical events", "easy", 3),
                     ("Világtörténet", "World history", "easy", 3)],
        "grade-10": [("Magyarország története", "History of Hungary", "easy", 3),
                     ("Magyarország", "Hungary", "easy", 3),
                     ("Történelem", "History", "easy", 3),
                     ("Történelmi események", "Historical events", "easy", 3),
                     ("Világtörténet", "World history", "easy", 3)],
        "grade-11": [("Európa és világ története", "History of Europe and the world", "easy", 3),
                     ("Európa", "Europe", "easy", 3),
                     ("Világ", "World", "easy", 3),
                     ("Történelem", "History", "easy", 3),
                     ("Történelmi események", "Historical events", "easy", 3)],
        "grade-12": [("Történelem-erettségi", "History-maturity", "easy", 3),
                     ("Történelem", "History", "easy", 3),
                     ("Történelmi események", "Historical events", "easy", 3),
                     ("Világtörténet", "World history", "easy", 3),
                     ("Európa és világ", "Europe and world", "easy", 3)],
    },
    "geography": {
        "grade-07": [("Földrajzi képességek", "Geographic skills", "easy", 3),
                     ("Földrajz", "Geography", "easy", 3),
                     ("Földrajzi képességek", "Geographic skills", "easy", 3),
                     ("Földrajzi ismeretek", "Geographic knowledge", "easy", 3),
                     ("Földrajzi eszközök", "Geographic tools", "easy", 3)],
        "grade-08": [("Európa és Magyarország", "Europe and Hungary", "easy", 3),
                     ("Európa", "Europe", "easy", 3),
                     ("Magyarország", "Hungary", "easy", 3),
                     ("Földrajz", "Geography", "easy", 3),
                     ("Földrajzi ismeretek", "Geographic knowledge", "easy", 3)],
        "grade-09": [("Európa és világ", "Europe and world", "easy", 3),
                     ("Európa", "Europe", "easy", 3),
                     ("Világ", "World", "easy", 3),
                     ("Földrajz", "Geography", "easy", 3),
                     ("Földrajzi ismeretek", "Geographic knowledge", "easy", 3)],
        "grade-12": [("Földrajz-erettségi", "Geography-maturity", "easy", 3),
                     ("Földrajz", "Geography", "easy", 3),
                     ("Földrajzi ismeretek", "Geographic knowledge", "easy", 3),
                     ("Európa és világ", "Europe and world", "easy", 3),
                     ("Földrajzi eszközök", "Geographic tools", "easy", 3)],
    },
}

def generate_module(country_code, country_name, grade, subject, topic_info, module_num):
    """Generate a single test module."""
    topic_name, topic_en, difficulty, time_min = topic_info
    
    module_id = f"{grade}-{subject}-{topic_name.lower().replace(' ', '-')}-1.0.0"
    
    # Determine question types based on subject
    if subject == "math":
        question_types = ["multiple_choice", "multiple_choice", "multiple_choice", "essay", "dynamic_math"]
    elif subject in ["physics", "chemistry"]:
        question_types = ["multiple_choice", "multiple_choice", "essay", "dynamic_math", "multiple_choice"]
    elif subject == "biology":
        question_types = ["multiple_choice", "multiple_choice", "essay", "multiple_choice", "essay"]
    elif subject == "english":
        question_types = ["multiple_choice", "multiple_choice", "essay", "multiple_choice", "multiple_choice"]
    elif subject in ["civics", "history", "geography"]:
        question_types = ["multiple_choice", "multiple_choice", "essay", "multiple_choice", "multiple_choice"]
    else:  # science
        question_types = ["multiple_choice", "multiple_choice", "essay", "multiple_choice", "multiple_choice"]
    
    questions = []
    for i, q_type in enumerate(question_types):
        q_id = f"q-{i+1:03d}"
        topic_idx = i % len(SUBJECT_TOPICS.get(subject, {}).get(grade, [("Topic", "Topic", "easy", 3)]))
        
        if q_type == "multiple_choice":
            question = {
                "id": q_id,
                "question_type": "multiple_choice",
                "text": f"[{subject}] {topic_name} - Kérdés {i+1}: {topic_en}",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "rubric": None,
                "points": 5,
                "variables": [],
                "tags": [subject, topic_name.lower().replace(' ', '-'), grade],
                "difficulty": difficulty,
                "estimated_time_minutes": time_min,
                "curriculum_topic": f"{country_code.upper()}-{grade.upper()}-{subject.upper()}-{topic_name}",
                "learning_objective": topic_en
            }
        elif q_type == "essay":
            question = {
                "id": q_id,
                "question_type": "essay",
                "text": f"[{subject}] {topic_name} - Kérdés {i+1}: {topic_en}",
                "options": None,
                "correct_answer": f"Minta válasz a(z) {topic_name} témakörhöz.",
                "rubric": f"Pontszámítás: {time_min} pont. Értékelés: helyesség, teljesítettség, érvelés.",
                "points": time_min * 2,
                "variables": [],
                "tags": [subject, topic_name.lower().replace(' ', '-'), grade],
                "difficulty": difficulty,
                "estimated_time_minutes": time_min,
                "curriculum_topic": f"{country_code.upper()}-{grade.upper()}-{subject.upper()}-{topic_name}",
                "learning_objective": topic_en
            }
        else:  # dynamic_math
            # General randomizer: modulates numbers within allowed range while
            # preserving number type (integer, decimal, fraction) and magnitude.
            # All numbers in a question share the same category and magnitude.
            grade_num = int(grade.split('-')[1])
            
            # Determine number category and magnitude range based on grade level
            if grade_num <= 3:
                number_category = "integer"
                var_min, var_max = 1, 20
            elif grade_num <= 5:
                number_category = "integer"
                var_min, var_max = 1, 100
            elif grade_num <= 7:
                number_category = "decimal"
                var_min, var_max = 1, 100
            elif grade_num <= 9:
                number_category = "decimal"
                var_min, var_max = 1, 1000
            elif grade_num <= 11:
                number_category = "fraction"
                var_min, var_max = 1, 100
            else:
                number_category = "fraction"
                var_min, var_max = 1, 1000

            question = {
                "id": q_id,
                "question_type": "dynamic_math",
                "text": f"[{subject}] {topic_name} - Question {i+1}: {topic_en} [rand:{var_min}-{var_max}]",
                "options": None,
                "correct_answer": "calculated",
                "rubric": None,
                "points": 5,
                "variables": [
                    {
                        "name": "x",
                        "type": number_category,
                        "min": var_min,
                        "max": var_max,
                        "step": 1 if number_category == "integer" else 0.1
                    },
                    {
                        "name": "y",
                        "type": number_category,
                        "min": var_min,
                        "max": var_max,
                        "step": 1 if number_category == "integer" else 0.1
                    }
                ],
                "tags": [subject, topic_name.lower().replace(' ', '-'), grade, number_category],
                "difficulty": difficulty,
                "estimated_time_minutes": time_min,
                "curriculum_topic": f"{country_code.upper()}-{grade.upper()}-{subject.upper()}-{topic_name}",
                "learning_objective": topic_en
            }
        questions.append(question)
    
    total_points = sum(q["points"] for q in questions)
    
    module = {
        "metadata": {
            "id": module_id,
            "name": f"{topic_name} - {country_name} {grade}",
            "version": "1.0.0",
            "description": f"45-minute test on {topic_name} for {grade} students. Covers: {', '.join([t[1] for t in SUBJECT_TOPICS.get(subject, {}).get(grade, [])])}",
            "author": "PlannedEducation Curriculum Team",
            "author_id": "system",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tags": [subject, topic_name.lower().replace(' ', '-'), grade, country_code.lower()],
            "subject": subject,
            "grade_level": grade,
            "license": "CC-BY-4.0",
            "checksum": "",
            "curriculum": COUNTRY_CONFIGS[country_code]["curriculum"],
            "duration_minutes": 45,
            "total_points": total_points,
            "question_count": len(questions),
            "randomizer_enabled": subject in ["math", "physics", "chemistry"],
            "difficulty": difficulty,
            "prerequisites": [],
            "learning_objectives": [t[1] for t in SUBJECT_TOPICS.get(subject, {}).get(grade, [])]
        },
        "exam": {
            "title": f"{grade} {subject.title()} - {topic_name}",
            "description": f"Test on {topic_name} including {', '.join([t[1] for t in SUBJECT_TOPICS.get(subject, {}).get(grade, [])])}",
            "duration_minutes": 45,
            "instructions": "Answer all questions. Circle the correct answer. You have 45 minutes.",
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
                "randomizer_enabled": subject in ["math", "physics", "chemistry"],
                "randomizer_seed": None
            }
        },
        "questions": questions,
        "rubrics": []
    }
    
    # Calculate checksum
    import hashlib
    pkg_copy = module.copy()
    pkg_copy["metadata"] = pkg_copy["metadata"].copy()
    pkg_copy["metadata"]["checksum"] = ""
    checksum = hashlib.sha256(json.dumps(pkg_copy, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    module["metadata"]["checksum"] = checksum
    
    return module

def main():
    total_modules = 0
    
    for country_code, config in COUNTRY_CONFIGS.items():
        print(f"\n{'='*70}")
        print(f"Generating modules for {config['country_name']} ({country_code})")
        print(f"{'='*70}")
        
        for grade, subjects in config["grades"].items():
            for subject in subjects:
                topics = SUBJECT_TOPICS.get(subject, {}).get(grade, [])
                if not topics:
                    print(f"  WARNING: No topics for {grade}/{subject}, skipping")
                    continue
                
                for topic_idx, topic_info in enumerate(topics):
                    module = generate_module(country_code, config["country_name"], grade, subject, topic_info, topic_idx + 1)
                    
                    # Create directory structure
                    module_dir = os.path.join(MODULES_ROOT, country_code, grade, subject)
                    os.makedirs(module_dir, exist_ok=True)
                    
                    # Generate filename
                    topic_slug = topic_info[0].lower().replace(' ', '-').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ö', 'o').replace('ő', 'o').replace('ú', 'u').replace('ü', 'u').replace('ű', 'u')
                    filename = f"module-{topic_idx+1:02d}-{topic_slug}.json"
                    filepath = os.path.join(module_dir, filename)
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(module, f, indent=2, ensure_ascii=False)
                    
                    total_modules += 1
                    if total_modules % 10 == 0:
                        print(f"  Generated {total_modules} modules...")
    
    print(f"\n{'='*70}")
    print(f"Total modules generated: {total_modules}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
