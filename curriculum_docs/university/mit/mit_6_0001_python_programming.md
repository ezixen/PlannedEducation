# MIT 6.0001: Introduction to Computer Science and Programming in Python

- **Institution**: Massachusetts Institute of Technology (MIT)
- **Department**: Electrical Engineering and Computer Science (Course 6)
- **Level**: Undergraduate
- **Source**: MIT OpenCourseWare (https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/)
- **Course Description**: An introductory course aimed at students with little or no prior programming experience. It teaches computational problem solving, data structures, algorithm design, and modern Python programming paradigms.

---

## Course Syllabus & Core Units

### Unit 1: What is Computation, Branching, and Iteration
- Types of computation: Declarative vs. imperative knowledge, Turing completeness.
- Basic scalar types: `int`, `float`, `bool`, `str`, `NoneType`.
- Expressions, variables, and re-binding.
- Control flow: conditional branching (`if`, `elif`, `else`).
- Loop mechanics: `while` loops, `for` loops with `range()`.
- Algorithmic thinking: Guess-and-check, exhaustive enumeration, and bisection search.
- Floating point approximations, roundoff errors, and machine epsilon.

### Unit 2: Functions, Scoping, and Abstraction
- Decomposition and modularity: Function definitions, arguments, and return values.
- Variable scope: Global frame vs. local frame, name resolution, and environments.
- Specifications: Docstrings, preconditions, and postconditions.
- Recursion: Base cases, recursive steps, inductive reasoning (e.g. Fibonacci, Towers of Hanoi).

### Unit 3: Structured Types, Mutability, and Aliasing
- Compound scalar data types: Tuples (immutable sequences).
- Lists: Mutability, indexing, slicing, list comprehensions, iteration, and side-effects.
- Memory models: Aliasing vs. cloning (`deepcopy` vs reference copying).
- Higher-order functions: `map`, `filter`, lambda expressions.
- Dictionaries: Hash maps, key-value mappings, average $O(1)$ lookup, limitations of keys (hashability).

### Unit 4: Testing, Debugging, and Exceptions
- Defensive programming: Assertions (`assert`), type contracts.
- Testing strategies: Unit testing, integration testing, boundary cases, glass-box vs. black-box testing.
- Exception handling: `try`, `except`, `else`, `finally`, `raise`.
- Exceptions as control flow.

### Unit 5: Object-Oriented Programming (OOP)
- Classes, instances, and object state.
- Special methods / dunder methods: `__init__`, `__str__`, `__add__`, `__len__`, `__eq__`.
- Encapsulation, information hiding, getters, and setters.
- Inheritance: Subclasses, superclasses, method overriding, and polymorphism.

### Unit 6: Algorithmic Complexity
- Asymptotic notation: Big O ($O$), Big Theta ($\Theta$), Big Omega ($\Omega$).
- Complexity classes:
  - Constant time: $O(1)$
  - Logarithmic time: $O(\log n)$ (bisection search)
  - Linear time: $O(n)$
  - Log-linear time: $O(n \log n)$ (merge sort)
  - Polynomial / Quadratic time: $O(n^2)$ (bubble sort, selection sort)
  - Exponential time: $O(2^n)$ (subsets, recursive Fibonacci without memoization)

### Unit 7: Search and Sorting Algorithms
- Linear search vs. binary search.
- Selection sort and bubble sort.
- Merge sort: Divide-and-conquer strategy, proof of $O(n \log n)$ upper bound.

---

## Assessment Mapping in PlannedEducation
Assessment modules generated for MIT 6.0001:
1. `plans/test-modules/modules/university/mit/cs-6-0001/module-01-python-basics-computation.json`
2. `plans/test-modules/modules/university/mit/cs-6-0001/module-02-functions-recursion-data-structures.json`
3. `plans/test-modules/modules/university/mit/cs-6-0001/module-03-oop-and-complexity.json`
