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

COUNTRY_LANGUAGE_MAP = {
    "hungary": ("hu", "Magyar"),
    "germany": ("de", "Deutsch"),
    "austria": ("de", "Deutsch"),
    "switzerland": ("de", "Deutsch"),
    "uk": ("en", "English"),
    "usa": ("en", "English"),
    "canada": ("en", "English"),
    "australia": ("en", "English"),
    "ireland": ("en", "English"),
    "new_zealand": ("en", "English"),
    "eu": ("en", "English"),
    "finland": ("fi", "Suomi"),
    "netherlands": ("nl", "Nederlands"),
    "belgium": ("nl", "Nederlands"),
    "sweden": ("sv", "Svenska"),
    "norway": ("no", "Norsk"),
    "denmark": ("da", "Dansk"),
}

TOPIC_TRANSLATIONS = {
    "de": {
        "Counting to 10": "Zählen bis 10", "Addition to 10": "Addition bis 10", "Subtraction to 10": "Subtraktion bis 10",
        "Counting to 20": "Zählen bis 20", "Addition to 20": "Addition bis 20", "Counting to 100": "Zählen bis 100",
        "Addition to 100": "Addition bis 100", "Subtraction to 100": "Subtraktion bis 100",
        "Multiplication basics": "Multiplikation Grundlagen", "Division basics": "Division Grundlagen",
        "Counting to 1000": "Zählen bis 1000", "Addition to 1000": "Addition bis 1000", "Subtraction to 1000": "Subtraktion bis 1000",
        "Multiplication table": "Einmaleins", "Division table": "Divisionstabelle",
        "Decimal numbers": "Dezimalzahlen", "Decimal addition": "Dezimaladdition", "Decimal subtraction": "Dezimalsubtraktion",
        "Decimal multiplication": "Dezimalmultiplikation", "Decimal division": "Dezimaldivision",
        "Fraction basics": "Bruchrechnung Grundlagen", "Fraction addition": "Brüche addieren", "Fraction subtraction": "Brüche subtrahieren",
        "Fraction multiplication": "Brüche multiplizieren", "Fraction division": "Brüche dividieren",
        "General fractions": "Allgemeine Brüche", "Fraction operations": "Bruchoperationen",
        "Percentage basics": "Prozentrechnung Grundlagen", "Percentage calculation": "Prozentberechnung", "Proportional ratio": "Proportionale Zuordnung",
        "Rational numbers": "Rationale Zahlen", "Algebraic expressions": "Algebraische Ausdrücke", "Equations": "Gleichungen",
        "Geometry basics": "Geometrie Grundlagen", "Statistics basics": "Statistik Grundlagen",
        "Real numbers": "Reelle Zahlen", "Functions": "Funktionen", "Linear equations": "Lineare Gleichungen",
        "Geometry": "Geometrie", "Statistics": "Statistik", "Functions and limits": "Funktionen und Grenzwerte",
        "Differentiation": "Differentialrechnung", "Integration": "Integralrechnung", "Probability": "Wahrscheinlichkeitsrechnung",
        "Functions and statistics": "Funktionen und Statistik", "Differentiation and integration": "Analysis",
        "Probability calculation": "Wahrscheinlichkeitsberechnung", "Statistical analysis": "Statistische Analyse",
        "Mathematical analysis": "Mathematische Analysis",
        "Energy and force": "Energie und Kraft", "Forces and motion": "Kräfte und Bewegung", "Motion": "Bewegung",
        "Energy": "Energie", "Force": "Kraft", "Mechanics basics": "Mechanik Grundlagen", "Forces": "Kräfte",
        "Work": "Arbeit", "Mechanics": "Mechanik", "Waves": "Wellen", "Optics": "Optik",
        "Waves and optics": "Wellen und Optik", "Electromagnetism": "Elektromagnetismus", "Modern physics": "Moderne Physik",
        "Physics preparation": "Physik Abiturvorbereitung",
        "Substances and properties": "Stoffe und Eigenschaften", "Substance changes": "Stoffumwandlungen",
        "Chemical reactions": "Chemische Reaktionen", "Acids and bases": "Säuren und Basen", "Chemical equations": "Reaktionsgleichungen",
        "Structural chemistry": "Strukturchemie", "Organic chemistry basics": "Organische Chemie Grundlagen",
        "Chemical equilibrium": "Chemisches Gleichgewicht", "Organic chemistry": "Organische Chemie",
        "Cell biology and genetics": "Zellbiologie und Genetik", "Cell structure": "Zellaufbau", "Genetics basics": "Genetik Grundlagen",
        "Ecology": "Ökologie", "Ecological systems": "Ökosysteme", "Human body and health": "Menschlicher Körper und Gesundheit",
        "Human body structure": "Anatomie des Menschen", "Senses": "Sinnesorgane", "Perception": "Wahrnehmung", "Health": "Gesundheit",
        "Genetics": "Genetik", "Human physiology and immunology": "Humanphysiologie und Immunologie",
        "Human body physiology": "Physiologie des Menschen", "Immunology": "Immunologie",
        "Nature and environment": "Natur und Umwelt", "Plants and animals": "Pflanzen und Tiere", "Nature": "Natur",
        "Environment": "Umwelt", "Nature conservation": "Naturschutz",
        "State and law": "Staat und Recht", "State structure": "Staatsaufbau", "Law basics": "Rechtsgrundlagen",
        "Civil law": "Bürgerliches Recht", "Democracy and market economy": "Demokratie und Marktwirtschaft",
        "Democracy": "Demokratie", "Market economy": "Marktwirtschaft", "Politology and law-maturity": "Politik und Recht",
        "Politology": "Politikwissenschaft", "Law-maturity": "Rechtskunde",
        "Middle Ages and early modern period": "Mittelalter und Frühe Neuzeit", "Middle Ages": "Mittelalter",
        "Early modern period": "Frühe Neuzeit", "History": "Geschichte", "Historical events": "Historische Ereignisse",
        "Modern period - 19th century": "Neuzeit - 19. Jahrhundert", "Modern period": "Neuzeit", "19th century": "19. Jahrhundert",
        "History of the 20th century": "Geschichte des 20. Jahrhunderts", "20th century": "20. Jahrhundert",
        "World history": "Weltgeschichte", "History of Hungary": "Europäische Geschichte", "Hungary": "Mitteleuropa",
        "History of Europe and the world": "Geschichte Europas und der Welt", "Europe": "Europa", "World": "Welt",
        "History-maturity": "Geschichte Abiturvorbereitung", "Europe and world": "Europa und die Welt",
        "Geographic skills": "Geographische Kompetenzen", "Geography": "Geographie", "Geographic knowledge": "Geographisches Wissen",
        "Geographic tools": "Geographische Arbeitsmethoden", "Europe and Hungary": "Europa und Mitteleuropa",
        "Geography-maturity": "Geographie Abiturvorbereitung",
    },
    "fi": {
        "Nature and environment": "Luonto ja ympäristö", "Plants and animals": "Kasvit ja eläimet", "Nature": "Luonto",
        "Environment": "Ympäristö", "Nature conservation": "Luonnonsuojelu",
        "Counting to 10": "Laskeminen 10:een", "Addition to 10": "Yhteenlasku 10:een", "Subtraction to 10": "Vähennyslasku 10:een",
    },
    "nl": {
        "Nature and environment": "Natuur en milieu", "Plants and animals": "Planten en dieren", "Nature": "Natuur",
        "Environment": "Milieu", "Nature conservation": "Natuurbehoud",
        "Counting to 10": "Tellen tot 10", "Addition to 10": "Optellen tot 10", "Subtraction to 10": "Aftrekken tot 10",
    },
    "sv": {
        "Nature and environment": "Natur och miljö", "Plants and animals": "Växter och djur", "Nature": "Natur",
        "Environment": "Miljö", "Nature conservation": "Naturskydd",
        "Counting to 10": "Räkna till 10", "Addition to 10": "Addition till 10", "Subtraction to 10": "Subtraktion till 10",
    },
    "no": {
        "Nature and environment": "Natur og miljø", "Plants and animals": "Planter og dyr", "Nature": "Natur",
        "Environment": "Miljø", "Nature conservation": "Naturvern",
        "Counting to 10": "Telle til 10", "Addition to 10": "Addisjon til 10", "Subtraction to 10": "Subtraksjon til 10",
    },
    "da": {
        "Nature and environment": "Natur og miljø", "Plants and animals": "Planter og dyr", "Nature": "Natur",
        "Environment": "Miljø", "Nature conservation": "Naturbeskyttelse",
        "Counting to 10": "Tælle til 10", "Addition to 10": "Addition til 10", "Subtraction to 10": "Subtraktion til 10",
    },
}

LANGUAGE_TEMPLATES = {
    "hu": {
        "question_label": "Kérdés",
        "desc_tpl": "45 perces felmérő: {topic} ({grade}). Témakörök: {objectives}",
        "exam_desc_tpl": "Felmérő a(z) {topic} témakörből ({objectives})",
        "instructions": "Válaszolj minden kérdésre! Jelöld meg a helyes választ. Időkeret: 45 perc.",
        "essay_ans": "Minta válasz a(z) {topic} témakörhöz.",
        "essay_rubric": "Pontszámítás: {pts} pont. Értékelés: helyesség, teljesítettség, érvelés.",
    },
    "en": {
        "question_label": "Question",
        "desc_tpl": "45-minute assessment on {topic} for {grade} students. Covers: {objectives}",
        "exam_desc_tpl": "Assessment on {topic} including {objectives}",
        "instructions": "Answer all questions. Select or write the best answer. You have 45 minutes.",
        "essay_ans": "Sample answer for {topic}.",
        "essay_rubric": "Scoring: {pts} points. Evaluation criteria: accuracy, completeness, reasoning.",
    },
    "de": {
        "question_label": "Frage",
        "desc_tpl": "45-minütige Prüfung zum Thema {topic} ({grade}). Themen: {objectives}",
        "exam_desc_tpl": "Prüfung zum Thema {topic}: {objectives}",
        "instructions": "Beantworten Sie alle Fragen sorgfältig. Sie haben 45 Minuten Zeit.",
        "essay_ans": "Musterantwort zum Thema {topic}.",
        "essay_rubric": "Bewertung: {pts} Punkte. Kriterien: Richtigkeit, Vollständigkeit, Begründung.",
    },
    "fi": {
        "question_label": "Kysymys",
        "desc_tpl": "45 minuutin koe aiheesta {topic} ({grade}). Aiheet: {objectives}",
        "exam_desc_tpl": "Koe aiheesta {topic}: {objectives}",
        "instructions": "Vastaa kaikkiin kysymyksiin huolellisesti. Aikaa on 45 minuuttia.",
        "essay_ans": "Mallivastaus aiheeseen {topic}.",
        "essay_rubric": "Pisteytys: {pts} pistettä. Arviointi: oikeellisuus, kattavuus, perustelut.",
    },
    "nl": {
        "question_label": "Vraag",
        "desc_tpl": "Toets van 45 minuten over {topic} ({grade}). Onderwerpen: {objectives}",
        "exam_desc_tpl": "Toets over {topic}: {objectives}",
        "instructions": "Beantwoord alle vragen zorgvuldig. Je hebt 45 minuten de tijd.",
        "essay_ans": "Voorbeeldantwoord voor {topic}.",
        "essay_rubric": "Beoordeling: {pts} punten. Criteria: juistheid, volledigheid, argumentatie.",
    },
    "sv": {
        "question_label": "Fråga",
        "desc_tpl": "45-minuters prov i {topic} ({grade}). Omfattar: {objectives}",
        "exam_desc_tpl": "Prov i {topic}: {objectives}",
        "instructions": "Besvara alla frågor noggrant. Du har 45 minuter på dig.",
        "essay_ans": "Exempelsvar för {topic}.",
        "essay_rubric": "Bedömning: {pts} poäng. Kriterier: korrekthet, fullständighet, resonemang.",
    },
    "no": {
        "question_label": "Spørsmål",
        "desc_tpl": "45-minutters prøve i {topic} ({grade}). Emner: {objectives}",
        "exam_desc_tpl": "Prøve i {topic}: {objectives}",
        "instructions": "Svar på alle spørsmålene. Du har 45 minutter til rådighet.",
        "essay_ans": "Eksempelsvar for {topic}.",
        "essay_rubric": "Vurdering: {pts} poeng. Kriterier: korrekthet, fullstendighet, begrunnelse.",
    },
    "da": {
        "question_label": "Spørgsmål",
        "desc_tpl": "45-minutters prøve i {topic} ({grade}). Emner: {objectives}",
        "exam_desc_tpl": "Prøve i {topic}: {objectives}",
        "instructions": "Besvar alle spørgsmål omhyggeligt. Du har 45 minutter.",
        "essay_ans": "Eksempelsvar for {topic}.",
        "essay_rubric": "Bedømmelse: {pts} point. Kriterier: korrekthed, fuldstændighed, begrundelse.",
    },
}


def localize_topic(lang_code: str, topic_hu: str, topic_en: str) -> str:
    if lang_code == "hu":
        return topic_hu
    return TOPIC_TRANSLATIONS.get(lang_code, {}).get(topic_en, topic_en)


def generate_module(country_code, country_name, grade, subject, topic_info, module_num):
    """Generate a single test module in the country's native language."""
    topic_hu, topic_en, difficulty, time_min = topic_info
    lang_code, lang_name = COUNTRY_LANGUAGE_MAP.get(country_code, ("en", "English"))
    tpl = LANGUAGE_TEMPLATES.get(lang_code, LANGUAGE_TEMPLATES["en"])
    display_topic = localize_topic(lang_code, topic_hu, topic_en)

    module_id = f"{grade}-{subject}-{topic_hu.lower().replace(' ', '-')}-1.0.0"

    if subject == "math":
        question_types = ["multiple_choice", "multiple_choice", "multiple_choice", "essay", "dynamic_math"]
    elif subject in ["physics", "chemistry"]:
        question_types = ["multiple_choice", "multiple_choice", "essay", "dynamic_math", "multiple_choice"]
    elif subject == "biology":
        question_types = ["multiple_choice", "multiple_choice", "essay", "multiple_choice", "essay"]
    else:
        question_types = ["multiple_choice", "multiple_choice", "essay", "multiple_choice", "multiple_choice"]

    q_label = tpl["question_label"]
    questions = []
    for i, q_type in enumerate(question_types):
        q_id = f"q-{i+1:03d}"

        if q_type == "multiple_choice":
            question = {
                "id": q_id,
                "question_type": "multiple_choice",
                "text": f"[{subject}] {display_topic} - {q_label} {i+1}: {display_topic}",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "rubric": None,
                "points": 5,
                "variables": [],
                "tags": [subject, display_topic.lower().replace(' ', '-'), grade, lang_code],
                "difficulty": difficulty,
                "estimated_time_minutes": time_min,
                "curriculum_topic": f"{country_code.upper()}-{grade.upper()}-{subject.upper()}-{display_topic}",
                "learning_objective": display_topic
            }
        elif q_type == "essay":
            question = {
                "id": q_id,
                "question_type": "essay",
                "text": f"[{subject}] {display_topic} - {q_label} {i+1}: {display_topic}",
                "options": None,
                "correct_answer": tpl["essay_ans"].format(topic=display_topic),
                "rubric": tpl["essay_rubric"].format(pts=time_min * 2),
                "points": time_min * 2,
                "variables": [],
                "tags": [subject, display_topic.lower().replace(' ', '-'), grade, lang_code],
                "difficulty": difficulty,
                "estimated_time_minutes": time_min,
                "curriculum_topic": f"{country_code.upper()}-{grade.upper()}-{subject.upper()}-{display_topic}",
                "learning_objective": display_topic
            }
        else:  # dynamic_math
            grade_num = int(grade.split('-')[1])
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
                "text": f"[{subject}] {display_topic} - {q_label} {i+1}: {display_topic} [rand:{var_min}-{var_max}]",
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
                "tags": [subject, display_topic.lower().replace(' ', '-'), grade, number_category, lang_code],
                "difficulty": difficulty,
                "estimated_time_minutes": time_min,
                "curriculum_topic": f"{country_code.upper()}-{grade.upper()}-{subject.upper()}-{display_topic}",
                "learning_objective": display_topic
            }
        questions.append(question)

    total_points = sum(q["points"] for q in questions)
    objectives_list = [
        localize_topic(lang_code, t[0], t[1])
        for t in SUBJECT_TOPICS.get(subject, {}).get(grade, [])
    ]
    objectives_str = ", ".join(objectives_list)

    module = {
        "metadata": {
            "id": module_id,
            "name": f"{display_topic} - {country_name} {grade}",
            "version": "1.0.0",
            "description": tpl["desc_tpl"].format(topic=display_topic, grade=grade, objectives=objectives_str),
            "author": "PlannedEducation Curriculum Team",
            "author_id": "system",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tags": [subject, display_topic.lower().replace(' ', '-'), grade, country_code.lower(), lang_code],
            "subject": subject,
            "grade_level": grade,
            "language": lang_code,
            "language_name": lang_name,
            "country": country_code.lower(),
            "license": "CC-BY-4.0",
            "checksum": "",
            "curriculum": COUNTRY_CONFIGS[country_code]["curriculum"],
            "duration_minutes": 45,
            "total_points": total_points,
            "question_count": len(questions),
            "randomizer_enabled": subject in ["math", "physics", "chemistry"],
            "difficulty": difficulty,
            "prerequisites": [],
            "learning_objectives": objectives_list
        },
        "exam": {
            "title": f"{grade} {subject.title()} - {display_topic}",
            "description": tpl["exam_desc_tpl"].format(topic=display_topic, objectives=objectives_str),
            "duration_minutes": 45,
            "instructions": tpl["instructions"],
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

    import hashlib
    pkg_copy = module.copy()
    pkg_copy["metadata"] = pkg_copy["metadata"].copy()
    pkg_copy["metadata"]["checksum"] = ""
    checksum = hashlib.sha256(json.dumps(pkg_copy, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    module["metadata"]["checksum"] = checksum

    return module


def main():
    import hashlib
    from pathlib import Path

    total_modules = 0

    for country_code, config in COUNTRY_CONFIGS.items():
        print(f"Generating modules for {config['country_name']} ({country_code})")

        for grade, subjects in config["grades"].items():
            for subject in subjects:
                topics = SUBJECT_TOPICS.get(subject, {}).get(grade, [])
                if not topics:
                    continue

                for topic_idx, topic_info in enumerate(topics):
                    module = generate_module(country_code, config["country_name"], grade, subject, topic_info, topic_idx + 1)

                    module_dir = os.path.join(MODULES_ROOT, country_code, grade, subject)
                    os.makedirs(module_dir, exist_ok=True)

                    topic_slug = topic_info[0].lower().replace(' ', '-').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ö', 'o').replace('ő', 'o').replace('ú', 'u').replace('ü', 'u').replace('ű', 'u')
                    filename = f"module-{topic_idx+1:02d}-{topic_slug}.json"
                    filepath = os.path.join(module_dir, filename)

                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(module, f, indent=2, ensure_ascii=False)

                    total_modules += 1

    # Also ensure any pre-existing standalone module files in MODULES_ROOT have language/country metadata and valid checksums
    for json_path in Path(MODULES_ROOT).rglob("*.json"):
        rel_parts = json_path.relative_to(MODULES_ROOT).parts
        country_code = rel_parts[0].lower() if rel_parts else "usa"
        lang_code, lang_name = COUNTRY_LANGUAGE_MAP.get(country_code, ("en", "English"))
        pkg = json.loads(json_path.read_text(encoding="utf-8"))
        meta = pkg.get("metadata", {})
        if meta.get("language") != lang_code or meta.get("country") != country_code:
            meta["language"] = lang_code
            meta["language_name"] = lang_name
            meta["country"] = country_code
            tags = meta.get("tags", [])
            if isinstance(tags, list) and lang_code not in tags:
                tags.append(lang_code)
            meta["tags"] = tags
            pkg["metadata"] = meta
            pkg_copy = pkg.copy()
            pkg_copy["metadata"] = pkg_copy["metadata"].copy()
            pkg_copy["metadata"]["checksum"] = ""
            pkg["metadata"]["checksum"] = hashlib.sha256(
                json.dumps(pkg_copy, sort_keys=True, separators=(',', ':')).encode()
            ).hexdigest()
            json_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Total modules generated/updated: {total_modules}")


if __name__ == "__main__":
    main()
