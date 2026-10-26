# MIT 18.06: Linear Algebra

- **Institution**: Massachusetts Institute of Technology (MIT)
- **Department**: Mathematics (Course 18)
- **Instructor**: Prof. Gilbert Strang
- **Level**: Undergraduate
- **Source**: MIT OpenCourseWare (https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)
- **Course Description**: Fundamental course on linear algebra, vector spaces, matrix factorizations, eigenvalues, and applications to differential equations, networks, and signal processing.

---

## Course Syllabus & Core Units

### Unit 1: Ax = b and The Four Fundamental Subspaces
- Systems of linear equations: Gaussian elimination, row reduction, augmented matrices.
- Matrix operations, inverse matrices, and Gauss-Jordan elimination.
- Matrix factorizations: $A = LU$ and $PA = LU$.
- Vector spaces and subspaces: Subspaces of $\mathbb{R}^n$.
- The Four Fundamental Subspaces of a matrix $A \in \mathbb{R}^{m \times n}$:
  1. Column space $C(A)$ in $\mathbb{R}^m$, dimension $r$.
  2. Nullspace $N(A)$ in $\mathbb{R}^n$, dimension $n - r$.
  3. Row space $C(A^T)$ in $\mathbb{R}^n$, dimension $r$.
  4. Left nullspace $N(A^T)$ in $\mathbb{R}^m$, dimension $m - r$.
- Complete solution to $Ax = b$: $x = x_p + x_n$.
- Rank, independence, basis, and dimension. Fundamental Theorem of Linear Algebra.

### Unit 2: Orthogonality, Projections, and Least Squares
- Inner products, orthogonality, and orthogonal subspaces: $C(A)^\perp = N(A^T)$ and $C(A^T)^\perp = N(A)$.
- Projections onto lines and subspaces: Projection matrix $P = A(A^T A)^{-1} A^T$.
- Least squares approximation for overdetermined systems: Normal equations $A^T A \hat{x} = A^T b$.
- Orthogonal bases and Gram-Schmidt process: $QR$ factorization ($A = QR$).

### Unit 3: Determinants and Eigenvalues
- Properties of determinants: 10 core axiomatic properties, cofactor expansions, formula for $A^{-1}$.
- Cramer's Rule, volumes of parallelepipeds, and cross products.
- Eigenvalues and eigenvectors: Characteristic equation $\det(A - \lambda I) = 0$.
- Matrix diagonalization: $A = S \Lambda S^{-1}$.
- Difference equations and matrix powers: $u_k = A^k u_0$.
- Systems of differential equations: $du/dt = Au$.
- Symmetric matrices: Spectral theorem, orthogonal eigenvectors, real eigenvalues.
- Positive definite matrices: Tests via pivots, determinants, and eigenvalues; energy tests $x^T A x > 0$.

### Unit 4: Singular Value Decomposition (SVD) and Linear Transformations
- Singular Value Decomposition: $A = U \Sigma V^T$.
- Geometry of SVD: Mapping orthonormal basis of row space to orthonormal basis of column space.
- Pseudoinverse: Moore-Penrose inverse $A^+ = V \Sigma^+ U^T$.
- Linear transformations: Matrix representations with respect to generic bases, change of basis.

---

## Assessment Mapping in PlannedEducation
Assessment modules generated for MIT 18.06:
1. `plans/test-modules/modules/university/mit/math-18-06/module-01-linear-equations-lu-factorization.json`
2. `plans/test-modules/modules/university/mit/math-18-06/module-02-vector-spaces-eigenvalues-svd.json`
