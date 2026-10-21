# PlannedEducation Test Module Format Specification (.pepkg)

## Overview

Test modules are distributed as JSON or YAML files following the PlannedEducation package format. Each module represents a complete 45-minute test for a specific subject, grade, and topic.

## Package Structure

```json
{
  "metadata": {
    "id": "uuid-string",
    "name": "Module Name",
    "version": "1.0.0",
    "description": "Module description",
    "author": "Author Name",
    "author_id": "uuid-string",
    "created_at": "ISO-8601 timestamp",
    "updated_at": "ISO-8601 timestamp",
    "tags": ["tag1", "tag2"],
    "subject": "physics|chemistry|biology|science|english|math",
    "grade_level": "grade-10",
    "license": "CC-BY-4.0",
    "checksum": "sha256-hash",
    "curriculum": "singapore-moe",
    "duration_minutes": 45,
    "total_points": 100,
    "question_count": 20,
    "randomizer_enabled": true,
    "difficulty": "easy|medium|hard",
    "prerequisites": ["module-id-1", "module-id-2"]
  },
  "exam": {
    "title": "Exam Title",
    "description": "Exam description",
    "duration_minutes": 45,
    "instructions": "Student instructions",
    "settings": {
      "shuffle_questions": true,
      "shuffle_options": true,
      "show_results_immediately": false,
      "allow_review": true,
      "require_seb": false,
      "time_multiplier": 1.0,
      "passing_score": 60,
      "delivery_mode": "classroom",
      "allow_digital_hand_raise": false,
      "randomizer_enabled": true,
      "randomizer_seed": null
    }
  },
  "questions": [
    {
      "id": "uuid-string",
      "question_type": "multiple_choice|essay|dynamic_math",
      "text": "Question text with [rand:1-10] variables",
      "options": ["option1", "option2", "option3", "option4"],
      "correct_answer": "Correct answer text",
      "rubric": "Grading rubric for essay questions",
      "points": 5,
      "variables": [
        {
          "name": "x",
          "type": "integer",
          "min": 1,
          "max": 10,
          "step": 1
        }
      ],
      "tags": ["topic1", "topic2"],
      "difficulty": "easy|medium|hard",
      "estimated_time_minutes": 3,
      "curriculum_topic": "topic-code",
      "learning_objective": "What students should demonstrate"
    }
  ],
  "rubrics": [
    {
      "id": "uuid-string",
      "question_id": "question-uuid",
      "criteria": [
        {
          "id": "criterion-id",
          "description": "Criterion description",
          "points": 5,
          "keywords": ["keyword1", "keyword2"]
        }
      ],
      "total_points": 10
    }
  ]
}
```

## Question Types

### Multiple Choice
- `question_type`: "multiple_choice"
- `options`: Array of 2-6 option strings
- `correct_answer`: The correct option text
- `points`: 1-100

### Essay
- `question_type`: "essay"
- `rubric`: Detailed grading criteria
- `correct_answer`: Model answer (for teacher reference)
- `points`: 1-100

### Dynamic Math
- `question_type`: "dynamic_math"
- `text`: Question text with `[rand:min-max]` placeholders
- `correct_answer`: Formula or expression (may reference variables)
- `variables`: Array of variable definitions
- `points`: 1-100

## Randomizer Configuration

Variables use `[rand:min-max]` syntax in question text:

```
Calculate the force: F = [rand:1-10] kg × [rand:2-20] m/s²
```

Variables are replaced with random values when a student starts the exam. Each student gets different values.

### Variable Definition

```json
{
  "name": "mass",
  "type": "integer",
  "min": 1,
  "max": 10,
  "step": 1,
  "choices": null,
  "formula": null
}
```

## Module Settings

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

## Module Lifecycle

1. **Create**: Teacher creates module in Exam Editor
2. **Export**: Module exported as .pepkg.json or .pepkg.yaml
3. **Share**: Module shared via email, shared drive, or package repository
4. **Import**: Another teacher imports module into their account
5. **Edit**: Teacher customizes module for their class
6. **Resave**: Modified module saved as new version
7. **Reuse**: Module used for multiple classes/years

## Checksum Validation

SHA-256 checksum calculated over package content (excluding checksum field). Validated on import to detect corruption or tampering.

## File Naming Convention

```
grade-{grade}-{subject}-{topic}-{version}.pepkg.json
```

Examples:
- `grade-10-physics-mechanics-1.0.0.pepkg.json`
- `grade-07-science-forces-1.0.0.pepkg.json`
- `grade-12-chemistry-organic-1.0.0.pepkg.json`

## License

All modules default to CC-BY-4.0 (Creative Commons Attribution 4.0 International). Teachers can specify different licenses.
