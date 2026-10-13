# pepkg - PlannedEducation Package Registry CLI

Command-line tool for managing test packages in the PlannedEducation platform.

## Installation

```bash
# From source
cd pepkg
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Configuration

Create a `pepkg.yaml` config file in your project root or `~/.config/pepkg/config.yaml`:

```yaml
api_url: "http://localhost:8000"
token: "your-auth-token"  # Optional, can use 'pepkg auth login'
```

Or set environment variables:
```bash
export PEPKG_API_URL="http://localhost:8000"
export PEPKG_TOKEN="your-auth-token"
```

## Usage

### Authentication

```bash
# Login (stores token in config)
pepkg auth login

# Check status
pepkg auth status

# Logout
pepkg auth logout

# Register new account
pepkg auth register
```

### Package Management

```bash
# Export an exam as a package
pepkg package export --exam-id EXAM_ID --format json --output package.json

# Import a package
pepkg package import package.json

# Validate a package locally
pepkg validate package package.json

# List your packages
pepkg package list

# Download a package by ID
pepkg package download PACKAGE_ID --output package.json
```

### Publishing

```bash
# Publish a package (make public)
pepkg publish PACKAGE_ID

# Unpublish (make private)
pepkg unpublish PACKAGE_ID
```

### Search

```bash
# Search packages
pepkg search packages "algebra" --subject math --grade-level 10

# Browse public packages
pepkg search public --subject science --grade-level 12
```

### Validation

```bash
# Validate package locally (no API needed)
pepkg validate package package.json

# Strict mode (warnings as errors)
pepkg validate package package.json --strict
```

## Package Format

Packages are JSON or YAML files with this structure:

```json
{
  "metadata": {
    "id": "uuid",
    "name": "Package Name",
    "version": "1.0.0",
    "description": "Description",
    "author": "Author Name",
    "author_id": "user-id",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "tags": ["algebra", "grade-10"],
    "subject": "mathematics",
    "grade_level": "10",
    "license": "CC-BY-4.0",
    "checksum": "sha256..."
  },
  "exam": {
    "title": "Exam Title",
    "description": "Exam description",
    "duration_minutes": 60,
    "instructions": "Instructions...",
    "settings": {
      "shuffle_questions": false,
      "shuffle_options": false,
      "show_results_immediately": false,
      "allow_review": true,
      "require_seb": false,
      "time_multiplier": 1.0,
      "passing_score": 60
    }
  },
  "questions": [
    {
      "id": "q1",
      "question_type": "multiple_choice",
      "text": "What is 2+2?",
      "options": ["3", "4", "5", "6"],
      "correct_answer": "4",
      "rubric": "Basic addition",
      "points": 10,
      "variables": [],
      "tags": ["addition"],
      "difficulty": "easy",
      "estimated_time_minutes": 2
    }
  ],
  "rubrics": []
}
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Type check
mypy src/
```

## License

MIT License - see LICENSE file for details.