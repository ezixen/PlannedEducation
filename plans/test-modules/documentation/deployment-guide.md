# PlannedEducation — Module Deployment Guide

## Overview

This guide explains how to deploy test modules to the PlannedEducation platform so teachers can browse, import, and use them in their classrooms.

## Module Repository Structure

Modules are organized by grade and subject:

```
plans/test-modules/modules/
├── grade-01/
│   ├── science/
│   └── english/
├── grade-02/
│   ├── science/
│   └── english/
├── ...
├── grade-10/
│   ├── physics/
│   ├── chemistry/
│   ├── biology/
│   └── english/
├── grade-11/
│   ├── physics/
│   ├── chemistry/
│   ├── biology/
│   └── english/
└── grade-12/
    ├── physics/
    ├── chemistry/
    ├── biology/
    └── english/
```

## Deploying Modules to the Platform

### Method 1: Individual Teacher Import

1. Teacher navigates to **Teacher Dashboard → Import Module**
2. Uploads a `.pepkg.json` or `.pepkg.yaml` file
3. Reviews and imports the module
4. Module appears in the teacher's Module Library

### Method 2: Bulk Import (Admin)

1. Admin navigates to **Admin Dashboard → Module Repository**
2. Uploads multiple `.pepkg` files
3. Modules are available to all teachers in the school

### Method 3: Package Repository (Coming Soon)

Modules can be published to a central repository for school-wide sharing.

## Module Validation

Before deploying, validate each module:

```bash
# Validate package structure
POST /packages/validate
Content-Type: multipart/form-data
File: module.pepkg.json
```

Validation checks:
- Required fields present (metadata, exam, questions)
- Checksum validity
- Question structure validity
- Randomizer variable definitions

## Module Lifecycle Management

### Versioning

- Increment version when making changes (e.g., 1.0.0 → 1.0.1)
- Keep previous versions available for reference
- Document changes in module description

### Deletion

- Only module owners can delete their modules
- Deleted modules are removed from the library
- Exams created from deleted modules remain accessible

### Archiving

- Archive modules no longer in use
- Archived modules are hidden from browse but can be restored

## Security Considerations

- Modules contain answer keys; share only with authorized teachers
- Checksum validation prevents tampering
- Module import validates structure before saving
- Teachers can only edit modules they own

## Sample Module Deployment Workflow

1. **Curriculum team** creates modules for each grade/subject
2. **Modules are reviewed** for accuracy and alignment
3. **Modules are exported** as `.pepkg.json` files
4. **Admin imports modules** to school repository
5. **Teachers browse and import** modules to their library
6. **Teachers customize** modules for their class
7. **Teachers create exams** from modules
8. **Students take exams** with randomized values
9. **Teachers grade** and review results

## File Naming Convention

```
grade-{grade}-{subject}-{topic}-{version}.pepkg.json
```

Examples:
- `grade-10-physics-mechanics-1.0.0.pepkg.json`
- `grade-07-science-forces-1.0.0.pepkg.json`
- `grade-12-chemistry-organic-1.0.0.pepkg.json`

## Support

- **Admin Dashboard → Module Repository**: Manage school modules
- **Teacher Dashboard → Module Library**: Browse and import modules
- **Documentation**: plans/test-modules/documentation/
