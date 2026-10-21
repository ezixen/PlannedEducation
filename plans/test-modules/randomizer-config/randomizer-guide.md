# PlannedEducation Test Module Randomizer Configuration

## Overview

The randomizer system replaces `[rand:min-max]` placeholders in question text with random values when a student starts an exam. Each student gets different values, preventing cheating.

## Randomizer Configuration Files

### math-randomizer.json

```json
{
  "subject": "math",
  "variable_pattern": "[rand:min-max]",
  "variable_types": {
    "integer": {
      "description": "Whole number between min and max",
      "example": "[rand:1-100]"
    },
    "float": {
      "description": "Decimal number between min and max",
      "example": "[rand:1.0-10.0:0.1]"
    },
    "choice": {
      "description": "Random choice from list",
      "example": "[rand:choice:red,blue,green]"
    }
  },
  "default_ranges": {
    "elementary": { "min": 1, "max": 20 },
    "middle": { "min": 1, "max": 100 },
    "high": { "min": 1, "max": 1000 }
  },
  "formula_support": true,
  "example_question": "Calculate: [rand:1-10] + [rand:1-10] = ?",
  "example_answer": "Variable sum of two random integers"
}
```

### chemistry-randomizer.json

```json
{
  "subject": "chemistry",
  "variable_pattern": "[rand:min-max]",
  "variable_types": {
    "integer": {
      "description": "Whole number for stoichiometry coefficients",
      "example": "[rand:1-5]"
    },
    "float": {
      "description": "Decimal for molar mass, concentration",
      "example": "[rand:0.1-2.0:0.1]"
    },
    "choice": {
      "description": "Random element or compound",
      "example": "[rand:choice:NaCl,H2O,CO2]"
    }
  },
  "default_ranges": {
    "coefficients": { "min": 1, "max": 5 },
    "concentration": { "min": 0.1, "max": 2.0, "step": 0.1 },
    "temperature": { "min": 20, "max": 100 },
    "volume": { "min": 10, "max": 500 }
  },
  "formula_support": true,
  "example_question": "Calculate moles: [rand:1-100] g of [rand:choice:NaCl,H2O,CO2]",
  "example_answer": "Variable moles based on random mass and compound"
}
```

### physics-randomizer.json

```json
{
  "subject": "physics",
  "variable_pattern": "[rand:min-max]",
  "variable_types": {
    "integer": {
      "description": "Whole number for mass, force, distance",
      "example": "[rand:1-100]"
    },
    "float": {
      "description": "Decimal for velocity, acceleration, time",
      "example": "[rand:1.0-50.0:0.1]"
    },
    "choice": {
      "description": "Random unit or material",
      "example": "[rand:choice:kg,m,s,N]"
    }
  },
  "default_ranges": {
    "mass": { "min": 1, "max": 100 },
    "force": { "min": 1, "max": 1000 },
    "distance": { "min": 1, "max": 1000 },
    "time": { "min": 1, "max": 60 },
    "velocity": { "min": 1, "max": 100 },
    "acceleration": { "min": 1, "max": 20 }
  },
  "formula_support": true,
  "example_question": "Calculate force: F = [rand:1-100] kg × [rand:1-20] m/s²",
  "example_answer": "Variable force based on random mass and acceleration"
}
```

## Randomizer Implementation

### Replacement Logic

When a student starts an exam:
1. Parse all question text for `[rand:min-max]` patterns
2. Generate random values for each variable
3. Replace variables in question text
4. Store generated values in the student's submission
5. Use stored values for grading (ensures consistency)

### Example

**Question Template:**
```
A [rand:1-10] kg object accelerates at [rand:1-20] m/s². Calculate the force.
```

**Student A sees:**
```
A 5 kg object accelerates at 8 m/s². Calculate the force.
```
**Correct answer:** 40 N

**Student B sees:**
```
A 3 kg object accelerates at 15 m/s². Calculate the force.
```
**Correct answer:** 45 N

### Consistency

The same variable value is used consistently across all questions in a submission that reference the same variable name.

## Configuration Per Module

Each module can specify its own randomizer settings:

```json
{
  "randomizer_enabled": true,
  "randomizer_seed": null,
  "variables": [
    {
      "name": "mass",
      "type": "integer",
      "min": 1,
      "max": 100,
      "step": 1
    }
  ]
}
```

If `randomizer_seed` is set, all students get the same values (useful for practice). If null, each student gets unique values.
