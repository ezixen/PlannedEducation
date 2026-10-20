# PlannedEducation — Test Module Plan (Grades 1-12 Sciences)

## Overview

This plan documents the creation of comprehensive, professional test modules for science subjects across grades 1-12 (elementary to high school). Modules are designed to be browsable, editable, reusable, and shareable via the PlannedEducation package system.

## Curriculum Standards Research

### Countries Selected

| Country | Source URL | Status | Curriculum Type |
|---------|------------|--------|-----------------|
| Hungary | https://www.oktatas.hu | Pending | National Core Curriculum (NAT) |
| Germany | https://www.kmk.org | Pending | State-level curricula (Bildungspläne) |
| UK | https://www.gov.uk/national-curriculum | Pending | National Curriculum (England) |
| USA | https://www.nextgenscience.org | Pending | NGSS (Next Generation Science Standards) |
| Canada | https://www.dcp.edu.gov.on.ca | Pending | Ontario Curriculum |

### Recommended Standards

**Hungary (NAT)** - Central European curriculum with strong science focus
**Germany (Bildungspläne)** - State-level curricula with strong science tradition
**UK (National Curriculum)** - Clear key stage progression
**USA (NGSS)** - Three-dimensional science learning
**Canada (Ontario)** - Comprehensive provincial curriculum

## Module Folder Structure

```
plans/test-modules/
├── README.md                          # Module system overview
├── curriculum-standards.md            # Country standards comparison
├── grade-structure.md                 # Grade-to-subject mapping per country
├── modules/                           # All test modules organized by country
│   ├── hungary/                       # Hungary - NAT Curriculum
│   │   ├── grade-01/                  # Grade 1 (age 7)
│   │   │   ├── science/               # Combined science
│   │   │   │   ├── module-01-living-things.json
│   │   │   │   └── module-02-materials.json
│   │   │   └── english/               # English language
│   │   │       ├── module-01-phonics.json
│   │   │       └── module-02-simple-sentences.json
│   │   ├── grade-02/                  # Grade 2 (age 8)
│   │   ├── grade-03/                  # Grade 3 (age 9)
│   │   ├── grade-04/                  # Grade 4 (age 10)
│   │   ├── grade-05/                  # Grade 5 (age 11)
│   │   ├── grade-06/                  # Grade 6 (age 12)
│   │   ├── grade-07/                  # Grade 7 (age 13)
│   │   ├── grade-08/                  # Grade 8 (age 14)
│   │   ├── grade-09/                  # Grade 9 (age 15)
│   │   ├── grade-10/                  # Grade 10 (age 16)
│   │   │   ├── physics/
│   │   │   ├── chemistry/
│   │   │   ├── biology/
│   │   │   └── english/
│   │   ├── grade-11/                  # Grade 11 (age 17)
│   │   │   ├── physics/
│   │   │   ├── chemistry/
│   │   │   ├── biology/
│   │   │   └── english/
│   │   └── grade-12/                  # Grade 12 (age 18)
│   │       ├── physics/
│   │       ├── chemistry/
│   │       ├── biology/
│   │       └── english/
│   ├── germany/                       # Germany - Bildungspläne
│   │   ├── grade-01/                  # Klasse 1
│   │   ├── grade-02/                  # Klasse 2
│   │   ├── grade-03/                  # Klasse 3
│   │   ├── grade-04/                  # Klasse 4
│   │   ├── grade-05/                  # Klasse 5
│   │   ├── grade-06/                  # Klasse 6
│   │   ├── grade-07/                  # Klasse 7
│   │   ├── grade-08/                  # Klasse 8
│   │   ├── grade-09/                  # Klasse 9
│   │   ├── grade-10/                  # Klasse 10
│   │   │   ├── physik/
│   │   │   ├── chemie/
│   │   │   ├── biologie/
│   │   │   └── englisch/
│   │   ├── grade-11/                  # Klasse 11
│   │   │   ├── physik/
│   │   │   ├── chemie/
│   │   │   ├── biologie/
│   │   │   └── englisch/
│   │   └── grade-12/                  # Klasse 12
│   │       ├── physik/
│   │       ├── chemie/
│   │       ├── biologie/
│   │       └── englisch/
│   ├── uk/                            # UK - National Curriculum (England)
│   │   ├── grade-01/                  # Year 1
│   │   ├── grade-02/                  # Year 2
│   │   ├── grade-03/                  # Year 3
│   │   ├── grade-04/                  # Year 4
│   │   ├── grade-05/                  # Year 5
│   │   ├── grade-06/                  # Year 6
│   │   ├── grade-07/                  # Year 7
│   │   ├── grade-08/                  # Year 8
│   │   ├── grade-09/                  # Year 9
│   │   ├── grade-10/                  # Year 10 (GCSE)
│   │   │   ├── physics/
│   │   │   ├── chemistry/
│   │   │   ├── biology/
│   │   │   └── english/
│   │   ├── grade-11/                  # Year 11 (GCSE)
│   │   │   ├── physics/
│   │   │   ├── chemistry/
│   │   │   ├── biology/
│   │   │   └── english/
│   │   └── grade-12/                  # Year 12 (A-Level)
│   │       ├── physics/
│   │       ├── chemistry/
│   │       ├── biology/
│   │       └── english/
│   ├── usa/                           # USA - NGSS
│   │   ├── grade-01/                  # Grade 1
│   │   ├── grade-02/                  # Grade 2
│   │   ├── grade-03/                  # Grade 3
│   │   ├── grade-04/                  # Grade 4
│   │   ├── grade-05/                  # Grade 5
│   │   ├── grade-06/                  # Grade 6
│   │   ├── grade-07/                  # Grade 7
│   │   ├── grade-08/                  # Grade 8
│   │   ├── grade-09/                  # Grade 9
│   │   ├── grade-10/                  # Grade 10
│   │   │   ├── physics/
│   │   │   ├── chemistry/
│   │   │   ├── biology/
│   │   │   └── english/
│   │   ├── grade-11/                  # Grade 11
│   │   │   ├── physics/
│   │   │   ├── chemistry/
│   │   │   ├── biology/
│   │   │   └── english/
│   │   └── grade-12/                  # Grade 12
│   │       ├── physics/
│   │       ├── chemistry/
│   │       ├── biology/
│   │       └── english/
│   └── canada/                        # Canada - Ontario Curriculum
│       ├── grade-01/                  # Grade 1
│       ├── grade-02/                  # Grade 2
│       ├── grade-03/                  # Grade 3
│       ├── grade-04/                  # Grade 4
│       ├── grade-05/                  # Grade 5
│       ├── grade-06/                  # Grade 6
│       ├── grade-07/                  # Grade 7
│   │   ├── grade-08/                  # Grade 8
│   │   ├── grade-09/                  # Grade 9
│   │   ├── grade-10/                  # Grade 10
│   │   │   ├── physics/
│   │   │   ├── chemistry/
│   │   │   ├── biology/
│   │   │   └── english/
│   │   ├── grade-11/                  # Grade 11
│   │   │   ├── physics/
│   │   │   ├── chemistry/
│   │   │   ├── biology/
│   │   │   └── english/
│   │   └── grade-12/                  # Grade 12
│   │       ├── physics/
│   │       ├── chemistry/
│   │       ├── biology/
│   │       └── english/
├── randomizer-config/                 # Randomizer settings per module
│   ├── math-randomizer.json           # Number randomization rules
│   ├── chemistry-randomizer.json      # Chemical formula randomization
│   └── physics-randomizer.json        # Variable randomization
└── documentation/
    ├── module-format-spec.md          # .pepkg format specification
    ├── randomizer-guide.md            # How randomizer works
    ├── teacher-guide.md               # How to browse/edit/reuse modules
    ├── deployment-guide.md            # How to deploy modules to server
    └── curriculum-standards.md        # Country standards comparison
```

## Subjects Per Grade

### Grades 1-3 (Lower Primary / Primary 1-3)
- Science (combined): Living things, materials, plants, animals, weather, light, sound
- English Language: Phonics, simple sentences, vocabulary, reading comprehension

### Grades 4-6 (Upper Primary / Primary 4-6)
- Science (combined): Cycles, systems, energy, interactions, forces
- English Language: Grammar, composition, comprehension, vocabulary

### Grades 7-9 (Lower Secondary / Secondary 1-3)
- Science (combined): Scientific method, cells, forces, energy, matter, chemical reactions
- English Language: Essay writing, comprehension, grammar, oral communication

### Grades 10-12 (Upper Secondary / Secondary 4-6)
- Physics: Mechanics, waves, electricity, magnetism, modern physics
- Chemistry: Atomic structure, bonding, reactions, stoichiometry, organic chemistry
- Biology: Cell biology, genetics, ecology, human physiology, evolution
- English Language: Advanced composition, comprehension, oral communication

## Test Module Format (.pepkg)

Each module contains:
- metadata: id, name, version, subject, grade, topic, duration, author, license
- exam: title, description, duration_minutes (45), settings (shuffle, randomizer)
- questions: array of question objects with type, text, options, correct_answer, rubric, points, variables
- rubrics: grading criteria per question

## Randomizer Configuration

- **Math**: [rand:1-10] variable replacement in numbers
- **Chemistry**: Chemical formula/equation variable replacement
- **Physics**: Variable values in word problems (mass, force, velocity, etc.)
- **Biology**: Minimal randomization (diagram labels, process steps)

## Module Settings Per Test

| Setting | Default | Description |
|---------|---------|-------------|
| duration_minutes | 45 | Standard class period |
| shuffle_questions | true | Randomize question order |
| shuffle_options | true | Randomize multiple choice options |
| randomizer_enabled | true | Enable variable randomization |
| randomizer_seed | null | Optional fixed seed for reproducibility |
| show_results_immediately | false | Don't show results until graded |
| allow_review | true | Allow students to review after grading |
| require_seb | false | Safe Exam Browser not required |
| time_multiplier | 1.0 | Standard time (IEP adjustments possible) |
| passing_score | 60 | 60% to pass |

## Next Steps

1. ✅ Create plan document with country-based structure
2. Research and finalize country standards (links above)
3. Create module folder structure by country
4. Create test modules for each grade/subject (45 minutes each)
5. Configure randomizer settings per subject
6. Test randomizer functionality
7. Test module browse/edit/resave/reuse workflow
8. Write extensive documentation
9. Commit and push to git

## Notes

- All tests are 45 minutes long (standard class period)
- No history or country-specific subjects (except English language)
- Physics included for all applicable grades
- Modules are JSON/YAML format compatible with PlannedEducation package system
- Randomizer uses [rand:min-max] syntax for variable replacement
- Teachers can browse, edit, resave, and reuse modules via Package Manager UI
- Each country has its own folder structure with grade and subject subfolders
