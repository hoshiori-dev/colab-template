# Geometric shift

How `digits.SmallCNN` trained on MNIST behaves when test digits are rotated, shifted and rescaled. "The perturbation"
below is one random draw per digit of rotation within ±20°, translation within ±3 pixels and scale within 0.85 to
1.15.

## What is established

- **Without augmentation the perturbation costs about 15 points.** After five epochs the model reaches 98.86% on
  clean test digits and 84.10% on perturbed ones
  ([003](../experiments/003-affine-augmentation/README.md)). The model was still improving on perturbed digits when
  training stopped, so 15 points is an upper estimate; the converged value is open (#10).
- **Augmenting with the same perturbation removes all but about one point of that gap.** The augmented model reaches
  97.45% on perturbed digits against 98.58% on clean ones. Its clean accuracy is 0.28 points below the unaugmented
  model's, a difference the size of the seed noise ([003](../experiments/003-affine-augmentation/README.md)).
- **The remaining gap of 1.1 points barely varies between seeds** (standard deviation 0.04 points). Whether it is
  information the perturbation destroys or a deficit training could remove is open (#9).

## How to measure here

- Accuracy on perturbed digits varies far more between seeds than accuracy on clean digits (standard deviation 0.90
  against 0.11 points for the unaugmented model in 003). Run at least three seeds and report the spread; a
  difference under a point on perturbed digits needs more.
- State whether the test perturbation and the training augmentation come from the same ranges. In 003 they do, which
  is the most favourable case for augmentation.
