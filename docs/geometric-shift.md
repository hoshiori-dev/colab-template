# Geometric shift

How a small CNN (two convolution blocks and one hidden layer, 105,866 parameters) trained on MNIST behaves when test
digits are rotated, shifted and rescaled. "The perturbation" below is one random draw per digit of rotation within
±20°, translation within ±3 pixels and scale within 0.85 to 1.15.

## What is established

- **Without augmentation the perturbation costs about 15 points.** After five epochs the model reaches 98.81% on
  clean test digits and 84.02% on perturbed ones
  ([003](../experiments/003-affine-augmentation/README.md)). The model was still improving on perturbed digits when
  training stopped, so 15 points is an upper estimate; the converged value is open (#10).
- **Augmenting with the same perturbation removes all but about one point of that gap.** The augmented model reaches
  97.46% on perturbed digits against 98.60% on clean ones. Its clean accuracy is 0.21 points below the unaugmented
  model's, a difference the size of the seed noise ([003](../experiments/003-affine-augmentation/README.md)).
- **Whether the remaining 1.1 points can be trained away is open** (#9). Across seeds the gap varies less than clean
  or perturbed accuracy do, which fits a fixed set of digits the perturbation makes unreadable, but two runs of three
  seeds disagree on how tight that is (standard deviation 0.04 and 0.11 points).

## How to measure here

- Accuracy on perturbed digits varies far more between seeds than accuracy on clean digits (standard deviation 1.03
  against 0.16 points for the unaugmented model in 003). Run at least three seeds and report the spread; a
  difference under a point on perturbed digits needs more.
- A seed does not pin the result. Two runs of 003 with the same seeds on the same GPU model, under different
  software environments, differ by up to 0.2 points per model while their means agree to within 0.1. Compare means
  and spreads, never single runs, and do not read structure into three numbers.
- State whether the test perturbation and the training augmentation come from the same ranges. In 003 they do, which
  is the most favourable case for augmentation.
