#!/usr/bin/env python3
"""
Advanced Math Randomizer for PlannedEducation
Handles number randomization at all levels: elementary to university mathematics
Supports: integers, decimals, fractions, complex numbers, matrices, vectors, 
polynomials, trigonometric expressions, calculus, linear algebra, and more.
"""

import random
import math
import fractions
import cmath
import json
from typing import Union, List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import math
import cmath


class NumberCategory(Enum):
    """Categories of numbers that can be randomized"""
    INTEGER = "integer"
    DECIMAL = "decimal"
    FRACTION = "fraction"
    COMPLEX = "complex"
    MATRIX = "matrix"
    VECTOR = "vector"
    POLYNOMIAL = "polynomial"
    TRIGONOMETRIC = "trigonometric"
    CALCULUS = "calculus"
    LINEAR_ALGEBRA = "linear_algebra"


@dataclass
class NumberRange:
    """Defines the range and constraints for number generation"""
    min_value: Union[int, float, complex]
    max_value: Union[int, float, complex]
    step: Union[int, float] = 1
    precision: int = 2  # decimal places for decimals
    allow_negative: bool = True
    allow_zero: bool = True
    # For fractions
    max_denominator: int = 100
    # For complex numbers
    real_range: Tuple[float, float] = (-100, 100)
    imag_range: Tuple[float, float] = (-100, 100)
    # For matrices/vectors
    dimensions: Tuple[int, int] = (2, 2)
    # For polynomials
    max_degree: int = 5
    # For trigonometric
    angle_unit: str = "radians"  # or "degrees"
    angle_range: Tuple[float, float] = (0, 2 * math.pi)


class NumberGenerator(ABC):
    """Abstract base class for number generators"""
    
    @abstractmethod
    def generate(self, range_config: NumberRange) -> Any:
        pass
    
    @abstractmethod
    def get_category(self) -> NumberCategory:
        pass


class IntegerGenerator:
    """Generates random integers within range"""
    
    @staticmethod
    def generate(min_val: int, max_val: int, step: int = 1, 
                 allow_negative: bool = True, allow_zero: bool = True) -> int:
        if not allow_negative:
            min_val = max(0, min_val)
        if not allow_zero and min_val <= 0 <= max_val:
            # Adjust range to exclude zero
            if min_val == 0:
                min_val = 1
            elif max_val == 0:
                max_val = -1
        
        # Ensure valid range
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        
        # Generate with step
        values = list(range(min_val, max_val + 1, max(1, abs(step))))
        if not allow_zero:
            values = [v for v in values if v != 0]
        if not allow_negative:
            values = [v for v in values if v >= 0]
        
        return random.choice(values) if values else 0


class DecimalGenerator:
    """Generates random decimals within range"""
    
    @staticmethod
    def generate(min_val: float, max_val: float, precision: int = 2,
                 step: float = 0.1, allow_negative: bool = True, 
                 allow_zero: bool = True) -> float:
        if not allow_negative:
            min_val = max(0, min_val)
        if not allow_zero and min_val <= 0 <= max_val:
            if min_val == 0:
                min_val = 10 ** (-precision)
            elif max_val == 0:
                max_val = -10 ** (-precision)
        
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        
        # Generate with precision
        scale = 10 ** precision
        min_scaled = int(min_val * scale)
        max_scaled = int(max_val * scale)
        step_scaled = max(1, int(step * scale))
        
        values = list(range(min_scaled, max_scaled + 1, max(1, step_scaled)))
        if not allow_zero:
            values = [v for v in values if v != 0]
        if not allow_negative:
            values = [v for v in values if v >= 0]
        
        return random.choice(values) / scale if values else 0.0


class FractionGenerator:
    """Generates random fractions within range"""
    
    @staticmethod
    def generate(min_val: float, max_val: float, max_denominator: int = 100,
                 allow_negative: bool = True, allow_zero: bool = True) -> fractions.Fraction:
        if not allow_negative:
            min_val = max(0, min_val)
        
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        
        # Generate random fraction
        for _ in range(100):  # max attempts
            denom = random.randint(1, max_denominator)
            num_min = int(min_val * denom)
            num_max = int(max_val * denom)
            
            if num_min > num_max:
                num_min, num_max = num_max, num_min
            
            numerator = random.randint(num_min, num_max)
            frac = fractions.Fraction(numerator, denom)
            
            if not allow_negative and frac < 0:
                continue
            if not allow_zero and frac == 0:
                continue
            
            return frac
        
        return fractions.Fraction(0, 1)


class ComplexGenerator:
    """Generates random complex numbers within range"""
    
    @staticmethod
    def generate(real_range: Tuple[float, float] = (-100, 100),
                 imag_range: Tuple[float, float] = (-100, 100),
                 allow_zero: bool = True) -> complex:
        real_min, real_max = real_range
        imag_min, imag_max = imag_range
        
        real = random.uniform(real_min, real_max)
        imag = random.uniform(imag_min, imag_max)
        
        if not allow_zero and abs(real) < 1e-10 and abs(imag) < 1e-10:
            return ComplexGenerator.generate(real_range, imag_range, allow_zero)
        
        return complex(real, imag)


class MatrixGenerator:
    """Generates random matrices within range"""
    
    @staticmethod
    def generate(dimensions: Tuple[int, int] = (2, 2),
                 value_range: Tuple[float, float] = (-10, 10),
                 number_type: str = "decimal",
                 allow_singular: bool = True) -> List[List[float]]:
        rows, cols = dimensions
        min_val, max_val = value_range
        
        for _ in range(10):  # max attempts
            matrix = []
            for _ in range(rows):
                row = []
                for _ in range(cols):
                    if number_type == "integer":
                        val = random.randint(int(min_val), int(max_val))
                    elif number_type == "fraction":
                        val = FractionGenerator.generate(-10, 10, 100)
                    else:
                        val = round(random.uniform(min_val, max_val), 2)
                    row.append(val)
                matrix.append(row)
            
            # Check if matrix is non-singular (for square matrices)
            if rows == cols and not allow_singular:
                # Simple determinant check for 2x2
                if rows == 2:
                    det = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
                    if abs(det) < 1e-10:
                        continue
            return matrix
        
        # Fallback: identity matrix
        return [[1 if i == j else 0 for j in range(cols)] for i in range(rows)]


class VectorGenerator:
    """Generates random vectors within range"""
    
    @staticmethod
    def generate(dimensions: int = 3,
                 value_range: Tuple[float, float] = (-10, 10),
                 number_type: str = "decimal") -> List[float]:
        min_val, max_val = value_range
        vector = []
        for _ in range(dimensions):
            if number_type == "integer":
                val = random.randint(int(value_range[0]), int(value_range[1]))
            elif number_type == "fraction":
                val = FractionGenerator.generate(-10, 10, 100)
            else:
                val = round(random.uniform(min_val, max_val), 2)
            vector.append(val)
        return vector


class PolynomialGenerator:
    """Generates random polynomials"""
    
    @staticmethod
    def generate(max_degree: int = 5,
                 coeff_range: Tuple[float, float] = (-10, 10),
                 number_type: str = "decimal",
                 variable: str = "x") -> Dict[str, Any]:
        min_val, max_val = coeff_range
        degree = random.randint(1, max_degree)
        
        coefficients = []
        for i in range(degree + 1):
            if i == degree:  # leading coefficient non-zero
                if number_type == "integer":
                    coeff = random.randint(1, int(max_val)) if max_val > 0 else random.randint(int(min_val), -1)
                elif number_type == "fraction":
                    coeff = FractionGenerator.generate(1, 10, 100)
                else:
                    coeff = round(random.uniform(0.1, max_val), 2)
            else:
                if number_type == "integer":
                    coeff = random.randint(int(min_val), int(max_val))
                elif number_type == "fraction":
                    coeff = FractionGenerator.generate(-10, 10, 100)
                else:
                    coeff = round(random.uniform(min_val, max_val), 2)
            coefficients.append(coeff)
        
        # Build polynomial string
        terms = []
        for i, coeff in enumerate(coefficients):
            power = degree - i
            if power == 0:
                terms.append(str(coeff))
            elif power == 1:
                terms.append(f"{coeff}x")
            else:
                terms.append(f"{coeff}x^{power}")
        
        poly_str = " + ".join(terms).replace("+ -", "- ")
        
        return {
            "degree": degree,
            "coefficients": coefficients,
            "variable": variable,
            "expression": poly_str
        }


class TrigonometricGenerator:
    """Generates random trigonometric expressions"""
    
    @staticmethod
    def generate(angle_unit: str = "radians",
                 angle_range: Tuple[float, float] = (0, 2 * math.pi),
                 functions: List[str] = None) -> Dict[str, Any]:
        if functions is None:
            functions = ["sin", "cos", "tan"]
        
        func = random.choice(functions)
        angle_min, angle_max = angle_range
        
        if angle_unit == "degrees":
            angle_deg = random.uniform(angle_min, angle_max)
            angle_rad = math.radians(angle_deg)
        else:
            angle_rad = random.uniform(angle_min, angle_max)
        
        # Compute value
        if func == "sin":
            value = math.sin(angle_rad)
        elif func == "cos":
            value = math.cos(angle_rad)
        elif func == "tan":
            value = math.tan(angle_rad)
        elif func == "sec":
            value = 1 / math.cos(angle_rad) if abs(math.cos(angle_rad)) > 1e-10 else float('inf')
        elif func == "csc":
            value = 1 / math.sin(angle_rad) if abs(math.sin(angle_rad)) > 1e-10 else float('inf')
        elif func == "cot":
            value = 1 / math.tan(angle_rad) if abs(math.tan(angle_rad)) > 1e-10 else float('inf')
        else:
            value = math.sin(angle_rad)
        
        return {
            "function": func,
            "angle": angle_rad if angle_unit == "radians" else angle_deg,
            "angle_unit": angle_unit,
            "value": value,
            "expression": f"{func}({angle_rad if angle_unit == 'radians' else angle_deg}°)"
        }


class CalculusGenerator:
    """Generates calculus expressions (derivatives, integrals)"""
    
    @staticmethod
    def generate_derivative(max_degree: int = 5,
                            coeff_range: Tuple[float, float] = (-5, 5),
                            variable: str = "x") -> Dict[str, Any]:
        # Generate polynomial
        poly = PolynomialGenerator.generate(
            max_degree=max_degree,
            coeff_range=(-5, 5),
            number_type="decimal"
        )
        
        # Compute derivative
        coeffs = poly["coefficients"]
        degree = poly["degree"]
        deriv_coeffs = []
        
        for i, coeff in enumerate(coeffs):
            power = degree - i
            if power > 0:
                deriv_coeffs.append(coeff * power)
        
        # Build derivative expression
        deriv_terms = []
        deriv_degree = degree - 1
        for i, coeff in enumerate(deriv_coeffs):
            power = deriv_degree - i
            if power == 0:
                deriv_terms.append(str(coeff))
            elif power == 1:
                deriv_terms.append(f"{coeff}x")
            else:
                deriv_terms.append(f"{coeff}x^{power}")
        
        deriv_expr = " + ".join(deriv_terms).replace("+ -", "- ")
        
        return {
            "original": poly["expression"],
            "derivative": deriv_expr,
            "variable": "x"
        }
    
    @staticmethod
    def generate_integral(max_degree: int = 4,
                          coeff_range: Tuple[float, float] = (-5, 5),
                          variable: str = "x") -> Dict[str, Any]:
        # Generate polynomial
        poly = PolynomialGenerator.generate(
            max_degree=max_degree,
            coeff_range=(-5, 5),
            number_type="decimal"
        )
        
        # Compute integral
        coeffs = poly["coefficients"]
        degree = poly["degree"]
        integral_coeffs = []
        
        for i, coeff in enumerate(coeffs):
            power = degree - i
            new_power = power + 1
            integral_coeffs.append(coeff / new_power)
        
        # Build integral expression
        terms = []
        for i, coeff in enumerate(integral_coeffs):
            power = degree - i + 1
            if power == 1:
                terms.append(f"{coeff}x")
            else:
                terms.append(f"{coeff}x^{power}")
        
        integral_expr = " + ".join(terms).replace("+ -", "- ") + " + C"
        
        return {
            "original": poly["expression"],
            "integral": integral_expr,
            "variable": "x"
        }


class LinearAlgebraGenerator:
    """Generates linear algebra problems"""
    
    @staticmethod
    def generate_system(equations: int = 2, variables: int = 2,
                        coeff_range: Tuple[float, float] = (-5, 5),
                        solution_type: str = "unique") -> Dict[str, Any]:
        """Generate a system of linear equations"""
        min_val, max_val = -5, 5
        
        if solution_type == "unique":
            # Generate matrix with non-zero determinant
            for _ in range(10):
                matrix = []
                for _ in range(equations):
                    row = [random.randint(-5, 5) for _ in range(variables)]
                    matrix.append(row)
                
                # Check determinant for square systems
                if equations == variables == 2:
                    det = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
                    if abs(det) > 1e-10:
                        break
            else:
                matrix = [[random.randint(-5, 5) for _ in range(variables)] for _ in range(equations)]
        
        # Generate solution vector
        solution = [random.randint(-5, 5) for _ in range(variables)]
        
        # Compute RHS
        rhs = []
        for row in matrix:
            val = sum(row[i] * solution[i] for i in range(variables))
            rhs.append(val)
        
        # Build equations
        equations_str = []
        for i, row in enumerate(matrix):
            terms = []
            for j, coeff in enumerate(row):
                if coeff != 0:
                    if coeff == 1:
                        terms.append(f"x{j+1}")
                    elif coeff == -1:
                        terms.append(f"-x{j+1}")
                    else:
                        terms.append(f"{coeff}x{j+1}")
            eq_str = " + ".join(terms).replace("+ -", "- ") + f" = {rhs[i]}"
            equations_str.append(eq_str)
        
        return {
            "equations": equations_str,
            "matrix": matrix,
            "rhs": rhs,
            "solution": solution,
            "variables": [f"x{i+1}" for i in range(variables)]
        }
    
    @staticmethod
    def generate_eigenvalue_problem(size: int = 2,
                                    value_range: Tuple[float, float] = (-5, 5)) -> Dict[str, Any]:
        """Generate matrix for eigenvalue problem"""
        matrix = MatrixGenerator.generate(
            dimensions=(size, size),
            value_range=(-5, 5),
            number_type="integer"
        )
        
        return {
            "matrix": matrix,
            "size": size,
            "description": f"Find eigenvalues and eigenvectors of this {size}x{size} matrix"
        }


class AdvancedMathRandomizer:
    """
    Main randomizer class that orchestrates all number generators.
    Provides a unified interface for generating math problems at any level.
    """
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self.generators = {
            NumberCategory.INTEGER: IntegerGenerator(),
            NumberCategory.DECIMAL: DecimalGenerator(),
            NumberCategory.FRACTION: FractionGenerator(),
            NumberCategory.COMPLEX: ComplexGenerator(),
            NumberCategory.MATRIX: MatrixGenerator(),
            NumberCategory.VECTOR: VectorGenerator(),
            NumberCategory.POLYNOMIAL: PolynomialGenerator(),
            NumberCategory.TRIGONOMETRIC: TrigonometricGenerator(),
            NumberCategory.CALCULUS: CalculusGenerator(),
            NumberCategory.LINEAR_ALGEBRA: LinearAlgebraGenerator(),
        }
    
    def generate_number(self, category: NumberCategory, 
                        range_config: NumberRange) -> Any:
        """Generate a number of the specified category within range"""
        generator = self.generators.get(category)
        if not generator:
            raise ValueError(f"No generator for category: {category}")
        
        # Handle different generator signatures
        if category == NumberCategory.INTEGER:
            return generator.generate(
                range_config.min_value, range_config.max_value, 
                range_config.step, range_config.allow_negative, range_config.allow_zero
            )
        elif category == NumberCategory.DECIMAL:
            return generator.generate(
                range_config.min_value, range_config.max_value,
                range_config.precision, range_config.step,
                range_config.allow_negative, range_config.allow_zero
            )
        elif category == NumberCategory.FRACTION:
            return generator.generate(
                range_config.min_value, range_config.max_value,
                range_config.max_denominator, range_config.allow_negative, range_config.allow_zero
            )
        elif category == NumberCategory.COMPLEX:
            return generator.generate(
                range_config.real_range, range_config.imag_range, range_config.allow_zero
            )
        elif category == NumberCategory.MATRIX:
            return generator.generate(
                range_config.dimensions, 
                (range_config.min_value, range_config.max_value),
                range_config.number_category if hasattr(range_config, 'number_category') else "decimal",
                range_config.allow_zero
            )
        elif category == NumberCategory.VECTOR:
            return generator.generate(
                range_config.dimensions[0] if isinstance(range_config.dimensions, tuple) else range_config.dimensions,
                (range_config.min_value, range_config.max_value),
                range_config.number_category if hasattr(range_config, 'number_category') else "decimal"
            )
        elif category == NumberCategory.POLYNOMIAL:
            return generator.generate(
                range_config.max_degree if hasattr(range_config, 'max_degree') else 5,
                (range_config.min_value, range_config.max_value),
                range_config.number_category if hasattr(range_config, 'number_category') else "decimal"
            )
        elif category == NumberCategory.TRIGONOMETRIC:
            return generator.generate(
                range_config.angle_unit if hasattr(range_config, 'angle_unit') else "radians",
                range_config.angle_range if hasattr(range_config, 'angle_range') else (0, 2 * math.pi)
            )
        elif category == NumberCategory.CALCULUS:
            return generator.generate_derivative(
                range_config.max_degree if hasattr(range_config, 'max_degree') else 5,
                (range_config.min_value, range_config.max_value)
            )
        elif category == NumberCategory.LINEAR_ALGEBRA:
            return generator.generate_system(
                range_config.dimensions[0] if isinstance(range_config.dimensions, tuple) else 2,
                range_config.dimensions[1] if isinstance(range_config.dimensions, tuple) else 2,
                (range_config.min_value, range_config.max_value)
            )
        else:
            # Fallback for other generators
            return generator.generate(range_config)
    
    def generate_question(self, subject: str, grade_level: int,
                          topic: str, question_type: str = "dynamic_math") -> Dict[str, Any]:
        """Generate a complete question with consistent number types"""
        # Determine number category based on grade and subject
        category = self._determine_category(subject, grade_level)
        
        # Get range config for grade level
        range_config = self._get_range_config(grade_level)
        
        # Generate numbers
        numbers = [self.generate_number(category, range_config) for _ in range(3)]
        
        return {
            "subject": subject,
            "grade": grade_level,
            "topic": topic,
            "question_type": question_type,
            "numbers": numbers,
            "category": category.value
        }
    
    def _determine_category(self, subject: str, grade: int) -> NumberCategory:
        """Determine number category based on subject and grade"""
        if subject in ["physics", "chemistry"]:
            if grade <= 5:
                return NumberCategory.INTEGER
            elif grade <= 8:
                return NumberCategory.DECIMAL
            else:
                return NumberCategory.FRACTION
        elif subject == "math":
            if grade <= 3:
                return NumberCategory.INTEGER
            elif grade <= 6:
                return NumberCategory.DECIMAL
            elif grade <= 9:
                return NumberCategory.FRACTION
            else:
                return NumberCategory.FRACTION
        else:
            return NumberCategory.INTEGER
    
    def _get_range_config(self, grade: int) -> NumberRange:
        """Get range configuration for grade level"""
        if grade <= 3:
            return NumberRange(min_value=1, max_value=20, step=1)
        elif grade <= 5:
            return NumberRange(min_value=1, max_value=100, step=1)
        elif grade <= 7:
            return NumberRange(min_value=1, max_value=100, step=0.1, precision=1)
        elif grade <= 9:
            return NumberRange(min_value=1, max_value=1000, step=0.1, precision=2)
        elif grade <= 11:
            return NumberRange(min_value=1, max_value=100, step=1, 
                              max_denominator=100)
        else:
            return NumberRange(min_value=1, max_value=1000, step=1,
                              max_denominator=1000)


# Convenience functions for easy use
def create_randomizer(seed: Optional[int] = None) -> AdvancedMathRandomizer:
    """Create a new randomizer instance"""
    return AdvancedMathRandomizer(seed)


def generate_math_question(subject: str, grade: int, topic: str,
                          question_type: str = "dynamic_math",
                          seed: Optional[int] = None) -> Dict[str, Any]:
    """Convenience function to generate a math question"""
    randomizer = AdvancedMathRandomizer(seed)
    return randomizer.generate_question(subject, grade, topic, question_type)


def generate_random_number(category: NumberCategory, 
                          min_val: Union[int, float] = 1,
                          max_val: Union[int, float] = 100,
                          number_type: str = "integer") -> Any:
    """Generate a single random number of specified category"""
    randomizer = AdvancedMathRandomizer()
    range_config = NumberRange(min_value=1, max_value=100)
    return randomizer.generate_number(category, range_config)


if __name__ == "__main__":
    # Demo usage
    randomizer = AdvancedMathRandomizer(42)
    
    # Generate various types of numbers
    print("=== Integer ===")
    print(IntegerGenerator.generate(1, 100))
    
    print("\n=== Decimal ===")
    print(DecimalGenerator.generate(1.0, 100.0, precision=2))
    
    print("\n=== Fraction ===")
    print(FractionGenerator.generate(1, 100, max_denominator=100))
    
    print("\n=== Complex ===")
    print(ComplexGenerator.generate())
    
    print("\n=== Matrix ===")
    print(MatrixGenerator.generate((3, 3)))
    
    print("\n=== Vector ===")
    print(VectorGenerator.generate(5))
    
    print("\n=== Polynomial ===")
    print(PolynomialGenerator.generate(4))
    
    print("\n=== Trigonometric ===")
    print(TrigonometricGenerator.generate())
    
    print("\n=== Calculus (Derivative) ===")
    print(CalculusGenerator.generate_derivative())
    
    print("\n=== Calculus (Integral) ===")
    print(CalculusGenerator.generate_integral())
    
    print("\n=== Linear Algebra (System) ===")
    print(LinearAlgebraGenerator.generate_system())
    
    print("\n=== Linear Algebra (Eigenvalue) ===")
    print(LinearAlgebraGenerator.generate_eigenvalue_problem(3))
    
    print("\n=== Full Question Generation ===")
    q = generate_math_question("math", 10, "quadratic equations", "dynamic_math", seed=42)
    print(json.dumps(q, indent=2, default=str))