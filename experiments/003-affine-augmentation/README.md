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
- **Model**: `SmallCNN` in `train.py`, two convolution blocks and one hidden layer, 105,866 parameters.
- **Arms**: `none` trains on the digits as they are; `affine` applies a fresh draw from the same perturbation family
  (`random_affine`, copied identically into `make_shifted.py` and `train.py`) to every training image in every batch.
  Nothing else differs.
- **Held fixed**: 5 epochs, batch size 128, Adam with learning rate 0.001, seeds 0, 1 and 2 per arm.
- **Measured**: accuracy on both test sets after every epoch; the answer uses the last epoch.

The augmentation and the perturbed test set draw from the same family and ranges, so this measures the best case for
augmentation: the shift is known in advance.

## Results

Accuracy after the fifth epoch, in percent, mean ± standard deviation over three seeds (`results/runs.csv`):

| Arm      | Clean test set | Perturbed test set | Gap (clean minus perturbed) |
| -------- | -------------- | ------------------ | --------------------------- |
| `none`   | 98.81 ± 0.16   | 84.02 ± 1.03       | 14.79 ± 0.92                |
| `affine` | 98.60 ± 0.20   | 97.46 ± 0.29       | 1.14 ± 0.11                 |

Mean accuracy after each epoch (`results/history.csv`):

| Epoch | `none` clean | `none` perturbed | `affine` clean | `affine` perturbed |
| ----- | ------------ | ---------------- | -------------- | ------------------ |
| 1     | 98.03        | 77.46            | 97.59          | 94.36              |
| 2     | 98.30        | 80.43            | 98.08          | 96.03              |
| 3     | 98.59        | 82.74            | 98.58          | 96.88              |
| 4     | 98.67        | 83.62            | 98.44          | 97.43              |
| 5     | 98.81        | 84.02            | 98.60          | 97.46              |

These numbers are from run `sweep-2`. An earlier run of the same sweep, `sweep-1`, was made with a previous version of
the launcher and is superseded; it gave 98.86 ± 0.11 and 84.10 ± 0.90 for `none`, and 98.58 ± 0.23 and 97.45 ± 0.19
for `affine`.

## Findings

**Augmentation helps but does not close the gap.** It raises accuracy on the perturbed set by 13.44 points, far more
than twice the larger seed standard deviation (1.03), and leaves a gap of 1.14 points to the model's own clean
accuracy. The rule set a gap of one point as closed, so by that rule it stays open, narrowly.

**The cost on clean digits is small and not established.** The augmented arm is 0.21 points lower on the clean test
set. With three seeds and standard deviations of 0.16 and 0.20 that difference is about the size of the noise.

Not asked, but observed:

- **The same seeds did not give the same numbers twice.** `sweep-1` and `sweep-2` ran the same training procedure
  with the same seeds on the same GPU model and differ in every figure, by up to 0.18 points on perturbed digits for
  a single model. Between them the code was restructured into one file and the environment changed (Python 3.12 in
  its own environment, then Colab's Python 3.13), so this does not say whether the GPU or the environment is the
  cause. Either way a seed fixes the initialization and the data order, not the result. The two runs agree on every
  mean to within 0.1 points.
- **A pattern in three seeds did not survive the second run.** In `sweep-1` the remaining gap of the augmented arm
  was almost the same in every seed (1.13, 1.09 and 1.17 points), which looked like a fixed set of digits that no
  model gets right. In `sweep-2` it is 1.25, 1.13 and 1.04. The gap still varies less than clean or perturbed
  accuracy do on their own, so the idea is not refuted, but three seeds were too few to call it. #9 asks the
  question properly.
- **Without augmentation, accuracy on the perturbed set was still climbing** when training stopped: 77.5% after one
  epoch, 84.0% after five, while clean accuracy moved by 0.8 points. Five epochs understate what the unaugmented
  model reaches, so the 14.79-point gap is an upper estimate of the gap at convergence. Asked as #10.
- **Accuracy off the training distribution is much noisier between seeds** than accuracy on it: 1.03 against 0.16
  for the unaugmented arm. Three seeds are enough for the size of this effect and would be too few for a small one.

Limits: one model size, five epochs, three seeds, and a test perturbation drawn from the same ranges as the
augmentation, which is the best case for augmentation.

## Reproduce

Run `sweep-2`, from commit `626cee47a9cc438921d5739e62df4e2dc4ae34d2` on one Colab T4, in this directory:

```sh
just shifted v1          # builds the perturbed set and uploads it to Drive; already done for v1
just sweep sweep-2       # = just run train.py --run sweep-2
just results sweep-2     # fetches the run and writes results/*.csv
```

Data read: `ylecun/mnist` at revision `77f3279092a1c1579b2250db8eafed0ad422088c`, and
`datasets/mnist-shifted/v1/shifted.npz` on Drive (sha256
`832edcd241448aea80c3750fa9f8aee3a8363ee2187c0f2a96f8a11122ce8be0`). The environment is `train.requirements.txt`
(PyTorch 2.15.0 with CUDA 13.2) installed over Colab's Python 3.13. The launch took four minutes, most of it
installing PyTorch; each of the six trainings took 6 to 8 seconds.

The weights to publish are `affine-seed0` of that run, which `train.py` copies to `deliver/`:
`just deliver sweep-2 discovery-loop/colab-template-mnist-cnn` (a person, after the merge).
