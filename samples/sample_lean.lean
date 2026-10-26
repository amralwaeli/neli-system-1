import Mathlib

example {M1 M2 c I : ℝ} (hM : M1 ≤ M2) (hc : 0 ≤ c) (hI : 0 < I) : (M1 * c) / I ≤ (M2 * c) / I := by
  have hmul : M1 * c ≤ M2 * c := by
    exact mul_le_mul_of_nonneg_right hM hc
  have hdiv : (M1 * c) / I ≤ (M2 * c) / I := by
    exact (div_le_div_iff_of_pos_right hI).2 hmul
  simpa [mul_comm, mul_left_comm, mul_assoc] using hdiv
