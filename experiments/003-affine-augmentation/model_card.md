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
| MNIST test split                                          | 98.51%   |
| The same digits under random rotation, shift and scale    | 97.26%   |

The perturbed set applies to every test digit one random draw of rotation within ±20°, translation within ±3 pixels
and scale within 0.85 to 1.15. Across three seeds the augmented models reach 98.60 ± 0.20% and 97.46 ± 0.29%; the
same network trained without augmentation reaches 98.81 ± 0.16% and 84.02 ± 1.03%. The experiment, its code and its
full results are in
[experiments/003-affine-augmentation](https://github.com/hoshiori-dev/colab-template/tree/main/experiments/003-affine-augmentation).

## Use

The repository has no package to install: the network is small enough to define where it is used.

```python
import torch
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
from torch import nn


class SmallCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(nn.Flatten(), nn.Linear(32 * 7 * 7, 64), nn.ReLU(), nn.Linear(64, 10))

    def forward(self, x):
        return self.classifier(self.features(x))


model = SmallCNN()
model.load_state_dict(load_file(hf_hub_download("discovery-loop/colab-template-mnist-cnn", "model.safetensors")))
model.eval()

# images: uint8 tensor of shape (N, 28, 28), white digit on black
logits = model(((images.float() / 255 - 0.1307) / 0.3081).unsqueeze(1))
```

## Limits

Trained and tested on MNIST only. Digits drawn with a different stroke width, in dark ink on a light background, or
perturbed beyond the ranges above are outside what was measured.
