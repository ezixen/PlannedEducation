# PlannedEducation Module System & School Federation Guide

PlannedEducation includes a decentralized, free, and open-source **Module System**. Teachers can package exams, dynamic question banks, grading rubrics, and answer keys into portable, self-contained educational modules (`.pepkg.json` or `.pepkg.yaml`). Schools can also federate with one another, allowing educators to browse, share, and synchronize curricula across classrooms and districts without reliance on proprietary vendors or paid services.

---

## 1. What is an Educational Module?

A PlannedEducation Module is an open-standard package format containing everything required to deliver and grade an assessment:

- **Metadata**: Title, version, author attribution, subject, category, grade level, license (e.g., Creative Commons CC-BY-4.0).
- **Questions**:
  - **Multiple Choice**: Question text, options, and randomized display definitions.
  - **Dynamic Math**: Formulaic expressions with customizable variable ranges (e.g., `[rand:2-10]`) so every student receives unique numbers.
  - **Essay & Free-Text**: Prompts, point values, and reference grading rubrics for automated or manual scoring.
- **Security & Integrity**: Every package includes a cryptographic SHA-256 checksum to guarantee that question content has not been corrupted or tampered with during transfer.

---

## 2. Supported Module Categories

The built-in catalog organizes modules into standard curriculum tracks:

| Category | Typical Subjects & Topics |
|---|---|
| **Mathematics** | Algebra, Geometry, Calculus, Statistics, Trigonometry |
| **Physics** | Mechanics, Energy, Electromagnetism, Thermodynamics, Optics |
| **Chemistry** | Organic, Inorganic, Stoichiometry, Solutions, Atomic Structure |
| **Biology** | Cellular Biology, Genetics, Ecology, Anatomy, Physiology |
| **Computer Science** | Programming Basics, Algorithms, Data Structures, Web Development |
| **Languages** | Reading Comprehension, Grammar, Literature, Vocabulary |
| **Arts & Humanities** | History, Geography, Civics, Philosophy, Visual Arts |
| **Health & PE** | Nutrition, First Aid, Exercise Science, Health Education |

---

## 3. Teacher Workflow: Creating & Exporting Modules

Teachers can turn any exam created in PlannedEducation into a reusable module:

1. **Create Exam**: In the Teacher Portal, navigate to **Exams** → **Create Exam**.
2. **Add Questions**: Add your questions, configure points, dynamic randomizers, and rubrics.
3. **Export Package**:
   - In the Exam details or Package Manager, select **Export Package**.
   - Choose whether to include answer keys and grading rubrics.
   - Click **Download Module File** to save the `.pepkg.json` file locally.
4. **Share Locally**: You can share this `.pepkg.json` file directly with colleagues via USB drive, local network share, or school email.

---

## 4. Teacher Workflow: Importing Modules

To use a shared module from a colleague or another school:

1. In the Teacher Portal, navigate to **Package Manager** → **Import Package**.
2. Upload the `.pepkg.json` file.
3. The system validates the file structure and checksum.
4. A brand new exam is automatically created in your account containing all questions, rubrics, and settings ready for immediate delivery or customization.

---

## 5. Publishing to the School Catalog

When a teacher wishes to make a module available to all other teachers on the school server:

1. Open **Package Manager** → **Publish to Catalog**.
2. Select your exam or uploaded module file.
3. Enter subject tags, target grade level, and license information.
4. Once published, any colleague logged into the school portal can discover and clone the module into their own classes with a single click.

---

## 6. School Federation: Connecting Schools Together

PlannedEducation is built from the ground up for **decentralized federation**. There is no central walled garden. Any school running PlannedEducation can publish modules and share them with partner schools across the district, region, or world.

### How School Federation Works

```
┌───────────────────────────────────────┐         ┌───────────────────────────────────────┐
│           School A (High School)      │         │           School B (Middle School)    │
│  • Teachers create Physics modules    │         │  • Configures School A as Source URL  │
│  • Publishes to:                      │ ──────> │  • Periodically synchronizes catalog  │
│    https://school-a.edu/packages      │  HTTP   │  • Teachers browse School A's modules │
└───────────────────────────────────────┘         └───────────────────────────────────────┘
```

### Adding a Partner School Source (Administrator / Teacher)

1. Navigate to **Package Manager** → **Manage Sources** → **Add Source**.
2. Enter the source details:
   - **Name**: A friendly name for the partner school (e.g., `Lincoln High STEM Repository`).
   - **URL**: The URL of the school's package endpoint (e.g., `https://lincoln.edu/packages`).
   - **Allowed Categories**: Filter the categories you wish to pull (e.g., `physics`, `mathematics`).
   - **Auto-Sync**: Enable automatic synchronization.
3. Click **Register Source**.

### Synchronizing Modules

- **Manual Sync**: Click **Sync Now** next to any configured source to immediately fetch newly published packages.
- **Automatic Sync**: The platform routinely refreshes package metadata from connected school sources in the background.
- Teachers can then search and filter across all connected sources directly from the catalog view.

---

## 7. Privacy & Zero-Knowledge Architecture

PlannedEducation strictly protects student privacy during module sharing:
- **No Student Data Export**: Modules contain only questions, rubrics, and curriculum metadata. Student names, IDs, grades, and submissions are never exported into package files.
- **Anonymized Attribution**: Authors can choose to publish with their teacher name or anonymously under a department umbrella.
- **Tamper Evident**: Checksum verification prevents any unauthorized modification of test items during transmission.

