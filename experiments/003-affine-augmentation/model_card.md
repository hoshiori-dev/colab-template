---
license: apache-2.0
library_name: pytorch
pipeline_tag: image-classification
datasets:
  - ylecun/mnist
tags:
  - mnist
---

# colab-template-mnist-cnn

A small convolutional network (105,866 parameters) that classifies 28 by 28 grayscale handwritten digits. It was
trained on MNIST with random affine augmentation, as the worked example of
[colab-template](https://github.com/hoshiori-dev/colab-template), a template for research projects that run on
Google Colab.

## Results

Accuracy of this checkpoint (arm `affine`, seed 0, five epochs):

| Test set                                                  | Accuracy |
| --------------------------------------------------------- | -------- |
| MNIST test split                                          | 98.55%   |
| The same digits under random rotation, shift and scale    | 97.42%   |

The perturbed set applies to every test digit one random draw of rotation within ±20°, translation within ±3 pixels
and scale within 0.85 to 1.15. Across three seeds the augmented models reach 98.58 ± 0.23% and 97.45 ± 0.19%; the
same network trained without augmentation reaches 98.86 ± 0.11% and 84.10 ± 0.90%. The experiment, its code and its
full results are in
[experiments/003-affine-augmentation](https://github.com/hoshiori-dev/colab-template/tree/main/experiments/003-affine-augmentation).

## Use

The model definition and the preprocessing live in the `digits` package of the repository.

```python
from digits import load_weights, to_input
from huggingface_hub import hf_hub_download

model = load_weights(hf_hub_download("discovery-loop/colab-template-mnist-cnn", "model.safetensors"))
logits = model(to_input(images))  # images: uint8 array of shape (N, 28, 28), white digit on black
```

## Limits

Trained and tested on MNIST only. Digits drawn with a different stroke width, in dark ink on a light background, or
perturbed beyond the ranges above are outside what was measured.
