# PlannedEducation — Teacher Guide: Test Module System

## Overview

The PlannedEducation Module System allows teachers to browse, create, edit, import, export, and share test modules. Modules are complete, ready-to-use tests that can be customized for any class.

## Module Format (.pepkg)

Modules are distributed as JSON or YAML files containing:
- **Metadata**: ID, name, version, subject, grade, topic, duration, author
- **Exam**: Title, description, duration, settings (shuffle, randomizer, etc.)
- **Questions**: Array of questions with type, text, options, answers, rubrics, points
- **Rubrics**: Grading criteria for essay questions

## Accessing the Module System

### Browsing Available Modules

1. Log in as a teacher
2. Navigate to **Teacher Dashboard → Module Library**
3. Browse modules by:
   - Grade level (Grade 1-12)
   - Subject (Science, Math, Physics, Chemistry, Biology, English)
   - Topic (e.g., Mechanics, Atomic Structure, Living Things)
   - Difficulty (Easy, Medium, Hard)
4. Use the search bar to find specific topics

### Previewing a Module

1. Click on any module in the library
2. View module details:
   - Full question list with answers and rubrics
   - Duration and total points
   - Curriculum alignment
   - Randomizer settings
3. Preview how questions will appear to students

## Creating a New Module

### From Scratch

1. Navigate to **Teacher Dashboard → Create Module**
2. Fill in module metadata:
   - Title, description, subject, grade level
   - Duration (default: 45 minutes)
   - Topic tags
3. Add questions:
   - Click **Add Question**
   - Select question type (Multiple Choice, Essay, Dynamic Math)
   - Enter question text, options, correct answer, rubric
   - For dynamic math, add `[rand:min-max]` variables
4. Configure exam settings:
   - Shuffle questions/options
   - Enable/disable randomizer
   - Set passing score
5. Click **Save Module**

### From Existing Exam

1. Navigate to **Teacher Exams**
2. Select an exam you own
3. Click **Export Package**
4. Choose format (JSON or YAML)
5. The package is downloaded as `.pepkg.json` or `.pepkg.yaml`

## Importing a Module

1. Navigate to **Teacher Dashboard → Import Module**
2. Upload a `.pepkg.json` or `.pepkg.yaml` file
3. Review the imported content:
   - Verify questions and answers
   - Check randomizer settings
   - Verify checksum integrity
4. Click **Import**
5. The module is added to your library

## Editing a Module

1. Navigate to **Teacher Dashboard → Module Library**
2. Select a module you own
3. Click **Edit Module**
4. Make changes:
   - Edit question text, options, answers
   - Add or remove questions
   - Change exam settings
   - Adjust randomizer variables
5. Click **Save** or **Save As New Version**

## Randomizer System

### How It Works

The randomizer replaces `[rand:min-max]` placeholders in question text with random values when a student starts the exam. Each student gets different values, preventing cheating.

### Example

**Question Template:**
```
A [rand:1-100] kg object accelerates at [rand:1-20] m/s². Calculate the force.
```

**Student A sees:**
```
A 5 kg object accelerates at 8 m/s². Calculate the force.
```
**Answer:** 40 N

**Student B sees:**
```
A 3 kg object accelerates at 15 m/s². Calculate the force.
```
**Answer:** 45 N

### Configuring Randomizer

When creating or editing a module:
1. Enable **Randomizer** in exam settings
2. Add variable definitions:
   - Name, type (integer/float/choice), min, max, step
3. Use `[rand:variable-name]` or `[rand:min-max]` in question text
4. Each student gets unique values on exam start

### Randomizer Settings Per Module

| Setting | Default | Description |
|---------|---------|-------------|
| randomizer_enabled | true | Enable variable replacement |
| randomizer_seed | null | Fixed seed (null = unique per student) |
| variables | [] | Array of variable definitions |

## Sharing Modules

### Exporting

1. Navigate to **Teacher Dashboard → Module Library**
2. Select a module you own
3. Click **Export**
4. Choose format (JSON or YAML)
5. Download the `.pepkg` file

### Importing from Colleagues

1. Receive a `.pepkg` file from a colleague
2. Navigate to **Teacher Dashboard → Import Module**
3. Upload the file
4. Review and import

### Module Repository (Coming Soon)

Modules can be published to a central repository for school-wide or district-wide sharing.

## Module Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| shuffle_questions | boolean | true | Randomize question order |
| shuffle_options | boolean | true | Randomize multiple choice options |
| randomizer_enabled | boolean | true | Enable [rand:min-max] replacement |
| randomizer_seed | string\|null | null | Fixed seed for reproducibility |
| show_results_immediately | boolean | false | Show results after submission |
| allow_review | boolean | true | Allow review after grading |
| require_seb | boolean | false | Safe Exam Browser required |
| time_multiplier | number | 1.0 | IEP accommodation multiplier |
| passing_score | number | 60 | Percentage to pass |
| duration_minutes | number | 45 | Test duration |

## Best Practices

1. **Use descriptive module names**: Include grade, subject, and topic
2. **Tag modules appropriately**: Makes them easier to find
3. **Set appropriate difficulty**: Helps teachers find appropriate tests
4. **Include rubrics**: Makes grading consistent and fair
5. **Test randomizer**: Verify variables generate valid questions
6. **Version your modules**: Increment version when making changes
7. **Add learning objectives**: Helps other teachers understand module purpose

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Module won't import | Check file format (.pepkg.json or .pepkg.yaml) |
| Checksum mismatch | File may be corrupted; re-download |
| Randomizer not working | Verify randomizer_enabled is true |
| Questions not shuffling | Check shuffle_questions setting |
| Can't edit module | Ensure you own the module or have edit permissions |

## Support

- **Teacher Dashboard → Help**: Access in-app help
- **Documentation**: docs/USER_MANUAL.md
- **Module Format Spec**: plans/test-modules/documentation/module-format-spec.md
- **Randomizer Guide**: plans/test-modules/randomizer-config/randomizer-guide.md
