# 003-affine-augmentation

Answers #3. Status: in progress

## Question

Does random affine augmentation during training close the accuracy gap between clean MNIST test digits and
affine-perturbed ones for a small CNN, and what does it cost on the clean digits?

The answer is "yes, it closes the gap" if the augmented arm's accuracy on the perturbed set is within one percentage
point of its own clean accuracy; "it helps but does not close it" if perturbed-set accuracy improves by more than twice
the larger of the two seed standard deviations while a gap of more than one point remains; "no" otherwise.

## Setup

- **Training data**: the `train` split of `ylecun/mnist` on the Hub (60,000 digits), revision
  `77f3279092a1c1579b2250db8eafed0ad422088c`.
- **Clean test set**: the `test` split of the same revision (10,000 digits).
- **Perturbed test set**: every clean test digit under one random draw of rotation within ±20°, translation within ±3
  pixels on each axis and scale within 0.85 to 1.15, bilinear interpolation, built by `make_shifted.py` with seed
  20261110. It is stored on Drive at `datasets/mnist-shifted/v1` and stands in for a private dataset.
- **Model**: `digits.SmallCNN`, 105,866 parameters.
- **Arms**: `none` trains on the digits as they are; `affine` applies a fresh draw from the same perturbation family
  (`affine.py`) to every training image in every batch. Nothing else differs.
- **Held fixed**: 5 epochs, batch size 128, Adam with learning rate 0.001, seeds 0, 1 and 2 per arm.
- **Measured**: accuracy on both test sets after every epoch; the answer uses the last epoch.

The augmentation and the perturbed test set draw from the same family and ranges, so this measures the best case for
augmentation: the shift is known in advance.

## Results

Not yet run.

## Findings

Not yet known.

## Reproduce

To be filled in with the commit, the commands and the run name once the runs exist.
