# 003-affine-augmentation

Answers #3. Pull request #8. Status: answered

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

Accuracy after the fifth epoch, in percent, mean ± standard deviation over three seeds (`results/runs.csv`):

| Arm      | Clean test set | Perturbed test set | Gap (clean minus perturbed) |
| -------- | -------------- | ------------------ | --------------------------- |
| `none`   | 98.86 ± 0.11   | 84.10 ± 0.90       | 14.76 ± 0.82                |
| `affine` | 98.58 ± 0.23   | 97.45 ± 0.19       | 1.13 ± 0.04                 |

Mean accuracy after each epoch (`results/history.csv`):

| Epoch | `none` clean | `none` perturbed | `affine` clean | `affine` perturbed |
| ----- | ------------ | ---------------- | -------------- | ------------------ |
| 1     | 98.06        | 77.58            | 97.53          | 94.30              |
| 2     | 98.35        | 80.51            | 98.06          | 95.97              |
| 3     | 98.62        | 82.85            | 98.60          | 96.94              |
| 4     | 98.64        | 83.39            | 98.45          | 97.44              |
| 5     | 98.86        | 84.10            | 98.58          | 97.45              |

## Findings

**Augmentation helps but does not close the gap.** It raises accuracy on the perturbed set by 13.35 points, far more
than twice the larger seed standard deviation (0.90), and leaves a gap of 1.13 points to the model's own clean
accuracy. The rule set a gap of one point as closed, so by that rule it stays open, narrowly.

**The cost on clean digits is small and not established.** The augmented arm is 0.28 points lower on the clean test
set. With three seeds and standard deviations of 0.11 and 0.23 that difference is about the size of the noise.

Not asked, but observed:

- **The remaining gap is nearly the same in every seed** (1.13, 1.09 and 1.17 points). Clean and perturbed accuracy
  each vary more between seeds than their difference does, which suggests a fixed set of perturbed digits that no
  seed gets right, for example digits pushed partly out of the frame. This experiment did not check that. Asked as
  #9.
- **Without augmentation, accuracy on the perturbed set was still climbing** when training stopped: 77.6% after one
  epoch, 84.1% after five, while clean accuracy moved by 0.8 points. Five epochs understate what the unaugmented
  model reaches, so the 14.76-point gap is an upper estimate of the gap at convergence. Asked as #10.
- **Accuracy off the training distribution is much noisier between seeds** than accuracy on it: 0.90 against 0.11
  for the unaugmented arm. Three seeds are enough for the size of this effect and would be too few for a small one.

Limits: one model size, five epochs, three seeds, and a test perturbation drawn from the same ranges as the
augmentation, which is the best case for augmentation.

## Reproduce

Everything ran from commit `0478c29e026ebab65888a6d7a76c2f19f0e609fc` on one Colab T4, as run `sweep-1`:

```sh
uv run python make_shifted.py                 # in this directory; builds the perturbed set locally
just drive-push experiments/003-affine-augmentation/data/mnist-shifted datasets/mnist-shifted/v1
just run 003-affine-augmentation --run sweep-1 -- python train.py
just bucket-pull 003-affine-augmentation sweep-1
uv run python collect.py ../../.local/out/003-affine-augmentation/sweep-1    # in this directory
```

Data read: `ylecun/mnist` at revision `77f3279092a1c1579b2250db8eafed0ad422088c`, and
`datasets/mnist-shifted/v1/shifted.npz` on Drive (sha256
`832edcd241448aea80c3750fa9f8aee3a8363ee2187c0f2a96f8a11122ce8be0`). The six trainings took 5 to 7 seconds each; the
launch spent several minutes before them creating the VM and installing the environment.

The published weights are `affine-seed0` of that run, prepared with
`just run 003-affine-augmentation --run sweep-1 -- python export.py`.
