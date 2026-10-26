example : ¬ (∀ n : Nat, n = 0) := by
  intro h
  have h1 : 1 = 0 := h 1
  simp at h1
