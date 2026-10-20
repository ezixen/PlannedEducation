#!/usr/bin/env python3
"""
Generate Hungary NAT Curriculum Test Modules for all grades 1-12.
Creates .pepkg.json files organized by grade and subject.
"""

import json
import os
from datetime import datetime, UTC
from pathlib import Path

# Base path for modules
BASE_PATH = Path("D:/Dev/PlannedEducation/plans/test-modules/modules/hungary")

# Hungary NAT Curriculum mapping by grade and subject
HUNGARY_CURRICULUM = {
    # Grades 1-4 (Lower Primary)
    "grade-01": {
        "hungarian": {"topic": "Betűk és hangok", "objectives": ["Megfejtés", "Olvasás", "Írás"]},
        "math": {"topic": "Számolás 10-ig", "objectives": ["Számlálás", "Összeadás", "Kivonás"]},
        "science": {"topic": "Élőlények", "objectives": ["Növények", "Állatok", "Ember"]},
        "ethics": {"topic": "Értékek és szabályok", "objectives": ["Tisztelet", "Segítségnyújtás", "Igazságosság"]},
    },
    "grade-02": {
        "hungarian": {"topic": "Olvasás és írás fejlesztése", "objectives": ["Folyamatos olvasás", "Helyesírás", "Szövegértés"]},
        "math": {"topic": "Számolás 100-ig", "objectives": ["Szorzás", "Osztás", "Mértekegységek"]},
        "science": {"topic": "Anyagok és tulajdonságaik", "objectives": ["Anyagok", "Állapotváltozások", "Anyagok használata"]},
        "ethics": {"topic": "Közösség és felelősség", "objectives": ["Család", "Iskola", "Környezetvédelem"]},
    },
    "grade-03": {
        "hungarian": {"topic": "Szövegértés és íráskészség", "objectives": ["Történetek", "Versek", "Személyes levelek"]},
        "math": {"topic": "Számolás 1000-ig", "objectives": ["Törtök", "Geometria", "Adatkezelés"]},
        "science": {"topic": "Növények és állatok", "objectives": ["Élővilág", "Ökológia", "Egészség"]},
        "ethics": {"topic": "Egyéni és közösségi értékek", "objectives": ["Önismeret", "Empátia", "Döntéshozatal"]},
    },
    "grade-04": {
        "hungarian": {"topic": "Komplex szövegértés és írás", "objectives": ["Szakmai szövegek", "Kreatív írás", "Nyelvtani ismeretek"]},
        "math": {"topic": "Számolás 10000-ig", "objectives": ["Tizedestörtök", "Mértékek", "Valószínűség"]},
        "science": {"topic": "Természet és környezet", "objectives": ["Környezetvédelem", "Energia", "Földrajz alapok"]},
        "ethics": {"topic": "Demokrácia és jogok", "objectives": ["Gyermekjogok", "Közösségi felelősség", "Tolerancia"]},
    },
    # Grades 5-8 (Upper Primary)
    "grade-05": {
        "hungarian": {"topic": "Irodalom és nyelvtan", "objectives": ["Klasszikus irodalom", "Nyelvtani elemzés", "Érvelés"]},
        "math": {"topic": "Racionális számok", "objectives": ["Törtök", "Százalékos számítás", "Algebra alapok"]},
        "science": {"topic": "Energia és erő", "objectives": ["Munka", "Energiafajták", "Egyszerű gépek"]},
        "ethics": {"topic": "Identitás és társadalom", "objectives": ["Személyiség", "Csoportdinamika", "Etikai dilemmák"]},
    },
    "grade-06": {
        "hungarian": {"topic": "Irodalomtörténet és kommunikáció", "objectives": ["Magyar irodalom", "Közbeszéd", "Médiaismeretterjesztés"]},
        "math": {"topic": "Valós számok és geometria", "objectives": ["Gyökök", "Háromszögek", "Koordináta-rendszer"]},
        "science": {"topic": "Anyag és változásai", "objectives": ["Kémia alapok", "Kémiai reakciók", "Anyagok keringése"]},
        "ethics": {"topic": "Emberi jogok és felelősség", "objectives": ["Alkotmány", "Nemzetközi jogok", "Aktív állampolgárság"]},
    },
    "grade-07": {
        "biology": {"topic": "Sejtbiológia és genetika", "objectives": ["Sejtfelépítés", "Osztódás", "Öröklődés"]},
        "chemistry": {"topic": "Alapkémia", "objectives": ["Elemek", "Vegyületek", "Reakciók"]},
        "physics": {"topic": "Mechanika alapok", "objectives": ["Mozgás", "Erők", "Energia"]},
        "history": {"topic": "Középkor és kora újkor", "objectives": ["Feudalizmus", "Felfedezések", "Vallási háborúk"]},
        "geography": {"topic": "Földrajzi képességek", "objectives": ["Térképek", "Klíma", "Gazdaság"]},
        "civics": {"topic": "Állam és jog", "objectives": ["Alkotmány", "Jogállam", "EU"]},
        "digital_culture": {"topic": "Digitális kultúra", "objectives": ["Informatika alapok", "Adatbiztonság", "Etika"]},
        "hungarian": {"topic": "Irodalom és nyelvtudat", "objectives": ["Klasszikusok", "Stílusgyakorlat", "Érvelés"]},
        "math": {"topic": "Algebra és geometria", "objectives": ["Egyenletek", "Síkidomok", "Függvények"]},
        "english": {"topic": "Angol nyelv A2", "objectives": ["Nyelvtan", "Szókincs", "Kommunikáció"]},
        "science": {"topic": "Erők és mozgás", "objectives": ["Newton-törvények", "Gravitáció", "Egyszerű gépek"]},
    },
    "grade-08": {
        "biology": {"topic": "Emberi test és egészség", "objectives": ["Rendszerek", "Egészség", "Prevenció"]},
        "chemistry": {"topic": "Szerves kémia alapok", "objectives": ["Szénvegyületek", "Élettani anyagok", "Környezetkémia"]},
        "physics": {"topic": "Hőtan és hullámok", "objectives": ["Hőenergia", "Hang", "Fény"]},
        "history": {"topic": "Újkor - 19. század", "objectives": ["Ipari forradalom", "Nemzetállamok", "Kolonizáció"]},
        "geography": {"topic": "Európa és Magyarország", "objectives": ["Tájak", "Népesség", "Gazdaság"]},
        "civics": {"topic": "Demokrácia és piacgazdaság", "objectives": ["Választások", "Gazdaság", "Szociális jogok"]},
        "digital_culture": {"topic": "Programozás és adatok", "objectives": ["Algoritmusok", "Adatbázisok", "Biztonság"]},
        "hungarian": {"topic": "Irodalom és kommunikáció", "objectives": ["Modern irodalom", "Szakmai kommunikáció", "Életrajz"]},
        "math": {"topic": "Függvények és statisztika", "objectives": ["Lineáris függvények", "Valószínűség", "Diagramok"]},
        "english": {"topic": "Angol nyelv B1", "objectives": ["Nyelvtan", "Olvasás", "Írás"]},
        "science": {"topic": "Környezet és fenntarthatóság", "objectives": ["Ökológia", "Klimaváltozás", "Megújuló energia"]},
        "ethics": {"topic": "Életút és karrier", "objectives": ["Önismeret", "Döntéshozatal", "Felelősség"]},
    },
    # Grades 9-12 (Gimnázium/Szakközépiskola)
    "grade-09": {
        "biology": {"topic": "Molekuláris biológia", "objectives": ["DNS", "Fehérjék", "Géntechnológia"]},
        "chemistry": {"topic": "Ásványi kémia", "objectives": ["Periódusos rendszer", "Vázlatkötés", "Oldatok"]},
        "physics": {"topic": "Elektromágnesesség", "objectives": ["Elektrostatikus", "Áramkörök", "Mágneses mező"]},
        "math": {"topic": "Függvények és határérték", "objectives": ["Polinomok", "Exponenciális", "Logaritmikus"]},
        "hungarian": {"topic": "Magyar irodalomtörténet", "objectives": ["Középkor", "Reneszánsz", "Barokk"]},
        "history": {"topic": "20. század története", "objectives": ["Világháboruk", "Hidegháború", "Rendszerváltás"]},
        "geography": {"topic": "Világföldrajz", "objectives": ["Kontinensek", "Globális problémák", "Fenntarthatóság"]},
        "civics": {"topic": "Nemzetközi kapcsolatok", "objectives": ["EU", "ENSZ", "Globális jog"]},
        "digital_culture": {"topic": "Informatika alapok", "objectives": ["Programozás", "Hálózatok", "Mesterséges intelligencia"]},
    },
    "grade-10": {
        "biology": {"topic": "Sejtbiológia és genetika", "objectives": ["Sejtciklus", "Mendel-törvények", "Génterápia"]},
        "chemistry": {"topic": "Atomfelépítés és kötések", "objectives": ["Kvantummechanika", "Kötéselmélet", "Reakciókinetika"]},
        "physics": {"topic": "Mechanika", "objectives": ["Kinematika", "Dynamika", "Energia-megmaradás"]},
        "math": {"topic": "Deriválás és integrálás", "objectives": ["Derivált", "Integrál", "Alkalmazások"]},
        "hungarian": {"topic": "Összeállítás és érvelés", "objectives": ["Esszé", "Vita", "Kritikai gondolkodás"]},
        "english": {"topic": "Angol nyelv B2", "objectives": ["Komplex nyelvtan", "Akadémiai írás", "Előadás"]},
        "history": {"topic": "Magyarország történelete", "objectives": ["Honfoglalás", "Történelem", "Mai Magyarország"]},
        "geography": {"topic": "Társadalomföldrajz", "objectives": ["Urbanizáció", "Globalizáció", "Regionális különbségek"]},
        "civics": {"topic": "Alkotmányjog és közigazgatás", "objectives": ["Alapvető jogok", "Közhatalom", "Közigazgatás"]},
        "digital_culture": {"topic": "Adatbázisok és web", "objectives": ["SQL", "HTML/CSS", "JavaScript alapok"]},
    },
    "grade-11": {
        "biology": {"topic": "Ökológia és evolúció", "objectives": ["Populációk", "Ökológiai rendszerek", "Evolúciós elmélet"]},
        "chemistry": {"topic": "Fizikális kémia", "objectives": ["Termodinamika", "Elektrokémia", "Felületi jelenségek"]},
        "physics": {"topic": "Hullámok és optika", "objectives": ["Hullámmechanika", "Geometriai optika", "Fizikai optika"]},
        "math": {"topic": "Valószínűség-számítás és statisztika", "objectives": ["Kombinatorika", "Eloszlások", "Statisztikai következtetés"]},
        "hungarian": {"topic": "Modern magyar irodalom", "objectives": ["20. század", "Mai irodalom", "Intertextualitás"]},
        "history": {"topic": "Európa és világ története", "objectives": ["Rendszerváltás", "EU", "Globális kihívások"]},
        "geography": {"topic": "Környezetföldrajz", "objectives": ["Katasztrófák", "Klimaváltozás", "Természeti erőforrások"]},
        "civics": {"topic": "Gazdaságjog és munkaerőpiac", "objectives": ["Munkajog", "Vállalkozás", "Társadalombiztosítás"]},
        "digital_culture": {"topic": "Szoftverfejlesztés", "objectives": ["OOP", "Verziókezelés", "Tesztelés"]},
    },
    "grade-12": {
        "biology": {"topic": "Emberi fiziólogia és immunológia", "objectives": ["Rendszerek", "Immunrendszer", "Betegségek"]},
        "chemistry": {"topic": "Analitikus és szerves kémia", "objectives": ["Spektroszkópia", "Szintézis", "Gyógyszerkémia"]},
        "physics": {"topic": "Modern fizika", "objectives": ["Relativitáselmélet", "Kvantumfizika", "Részecskefizika"]},
        "math": {"topic": "Végzettségi felkészülés", "objectives": ["Függvények", "Analízis", "Alkalmazott matematika"]},
        "hungarian": {"topic": "Érettségi felkészülés", "objectives": ["Olvasás", "Írás", "Szóbeli"]},
        "history": {"topic": "Történelem érettségi", "objectives": ["Korszakok", "Forráskritika", "Érvelés"]},
        "geography": {"topic": "Földrajz érettségi", "objectives": ["Térkép", "Statisztika", "Elemzés"]},
        "civics": {"topic": "Polológia és jog érettségi", "objectives": ["Rendszerek", "Jogalkotás", "Nemzetközi jog"]},
        "digital_culture": {"topic": "Projektmunka és portfólió", "objectives": ["Agile", "DevOps", "Karriertervezés"]},
    },
}

# Question templates by type
QUESTION_TEMPLATES = {
    "multiple_choice": {
        "question_type": "multiple_choice",
        "options": ["A", "B", "C", "D"],
        "points": 5,
    },
    "essay": {
        "question_type": "essay",
        "options": None,
        "points": 10,
    },
    "dynamic_math": {
        "question_type": "dynamic_math",
        "options": None,
        "points": 5,
    },
}

def generate_questions(subject, topic, objectives, grade_num):
    """Generate 10 questions for a module."""
    questions = []
    q_types = ["multiple_choice"] * 5 + ["essay"] * 3 + ["dynamic_math"] * 2
    
    for i, q_type in enumerate(q_types, 1):
        template = QUESTION_TEMPLATES[q_type]
        q = {
            "id": f"q-{i:03d}",
            "question_type": template["question_type"],
            "text": f"[{subject}] {topic} - Kérdés {i}: {objectives[i % len(objectives)]}",
            "options": template["options"],
            "correct_answer": template["options"][0] if template["options"] else f"Minta válasz a(z) {topic} témakörhöz.",
            "rubric": f"Pontszámítás: {template['points']} pont. Értékelés: helyesség, teljesítettség, érvelés." if q_type == "essay" else None,
            "points": template["points"],
            "variables": [],
            "tags": [subject.lower(), topic.lower().replace(" ", "-")],
            "difficulty": "medium" if grade_num >= 7 else "easy",
            "estimated_time_minutes": 5 if q_type == "essay" else 3,
            "curriculum_topic": f"HU-{grade_num:02d}-{subject.upper()[:4]}-{topic[:20]}",
            "learning_objective": objectives[i % len(objectives)],
        }
        questions.append(q)
    return questions

def create_module(grade, subject, data, grade_num):
    """Create a complete module JSON."""
    topic = data["topic"]
    objectives = data["objectives"]
    
    module_id = f"{grade}-{subject}-{topic.lower().replace(' ', '-').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ö','o').replace('ő','o').replace('ú','u').replace('ü','u').replace('ű','u')}-1.0.0"
    module_id = module_id[:80]  # Limit length
    
    now = datetime.now(UTC).isoformat()
    
    questions = generate_questions(subject, topic, objectives, grade_num)
    total_points = sum(q["points"] for q in questions)
    
    module = {
        "metadata": {
            "id": module_id,
            "name": f"{topic} - {grade.replace('grade-', 'Grade ').title()} {subject.capitalize()}",
            "version": "1.0.0",
            "description": f"45-minute test on {topic.lower()} for {grade.replace('grade-', 'Grade ')} students. Covers: {', '.join(objectives)}.",
            "author": "PlannedEducation Curriculum Team",
            "author_id": "system",
            "created_at": now,
            "updated_at": now,
            "tags": [subject.lower(), topic.lower().replace(" ", "-"), grade],
            "subject": subject.lower(),
            "grade_level": grade,
            "license": "CC-BY-4.0",
            "checksum": "",
            "curriculum": "hungary-nat",
            "duration_minutes": 45,
            "total_points": total_points,
            "question_count": len(questions),
            "randomizer_enabled": subject.lower() in ["math", "matematika", "physics", "fizika", "chemistry", "kémia"],
            "difficulty": "medium" if grade_num >= 7 else "easy",
            "prerequisites": [],
            "learning_objectives": objectives,
        },
        "exam": {
            "title": f"{grade.replace('grade-', 'Grade ').title()} {subject.capitalize()} - {topic}",
            "description": f"Test on {topic.lower()} including {', '.join(objectives).lower()}",
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
                "randomizer_enabled": subject.lower() in ["math", "matematika", "physics", "fizika", "chemistry", "kémia"],
                "randomizer_seed": None,
            },
        },
        "questions": questions,
        "rubrics": [],
    }
    
    # Calculate checksum
    import hashlib
    pkg_copy = module.copy()
    pkg_copy["metadata"] = pkg_copy["metadata"].copy()
    pkg_copy["metadata"]["checksum"] = ""
    content = json.dumps(pkg_copy, sort_keys=True, separators=(',', ':'))
    module["metadata"]["checksum"] = hashlib.sha256(content.encode()).hexdigest()
    
    return module

def main():
    print("Generating Hungary NAT Curriculum Test Modules...")
    
    total_modules = 0
    for grade, subjects in HUNGARY_CURRICULUM.items():
        grade_num = int(grade.split("-")[1])
        grade_path = BASE_PATH / grade
        
        for subject, data in subjects.items():
            subject_path = grade_path / subject.lower()
            subject_path.mkdir(parents=True, exist_ok=True)
            
            module = create_module(grade, subject, data, grade_num)
            
            # Create filename
            safe_topic = data["topic"].lower().replace(" ", "-").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ö","o").replace("ő","o").replace("ú","u").replace("ü","u").replace("ű","u")
            filename = f"module-01-{safe_topic}.json"
            filepath = subject_path / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(module, f, indent=2, ensure_ascii=False)
            
            print(f"  Created: {grade}/{subject}/{filename}")
            total_modules += 1
    
    print(f"\nTotal modules created: {total_modules}")
    print("Done!")

if __name__ == "__main__":
    main()