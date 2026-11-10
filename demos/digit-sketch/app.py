# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "gradio>=5",
#     "huggingface-hub>=0.30",
#     "numpy>=2",
#     "pillow>=10",
#     "safetensors>=0.4",
#     "torch>=2.6",
# ]
# ///
"""Draw a digit and see what the model from experiment 003 makes of it.

    just serve          # in this directory; or: uv run app.py

The weights come from the Hub repository below. While that repository is private, the
download needs a token that can read it: `just serve` passes HF_TOKEN from the project's
.env. Set DIGITS_WEIGHTS to a local model.safetensors to use a file instead.
"""

import os

import gradio as gr
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from PIL import Image
from safetensors.torch import load_file
from torch import nn

WEIGHTS_REPO = "discovery-loop/colab-template-mnist-cnn"
AS_MNIST = "Center and scale like MNIST"
AS_DRAWN = "Use the canvas as drawn"

# Mean and standard deviation of the MNIST training pixels scaled to [0, 1].
MEAN, STD = 0.1307, 0.3081


# SmallCNN and to_input are copied from experiments/003-affine-augmentation/train.py. The
# weights fit only this architecture and expect exactly this normalization, so a change
# there has to be copied here.
class SmallCNN(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 7 * 7, 64),
            nn.ReLU(),
            nn.Linear(64, 10),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def to_input(pixels: torch.Tensor) -> torch.Tensor:
    """Pixels in [0, 255] of shape (N, 28, 28) as the normalized tensor (N, 1, 28, 28) the model takes."""
    return pixels.float().div(255.0).sub(MEAN).div(STD).unsqueeze(1)


model = SmallCNN()
model.load_state_dict(load_file(os.environ.get("DIGITS_WEIGHTS") or hf_hub_download(WEIGHTS_REPO, "model.safetensors")))
model.eval()


def ink(sketch: dict) -> np.ndarray:
    """The drawing as floats in [0, 1], 1 where there is ink, whatever the canvas background."""
    rgba = np.asarray(Image.fromarray(sketch["composite"]).convert("RGBA"), dtype=np.float32) / 255
    return (1 - rgba[..., :3].mean(axis=-1)) * rgba[..., 3]


def as_mnist(drawing: np.ndarray) -> np.ndarray:
    """MNIST's own framing: the digit scaled into a 20 by 20 box and centered in 28 by 28."""
    rows, columns = np.nonzero(drawing > 0.1)
    box = drawing[rows.min() : rows.max() + 1, columns.min() : columns.max() + 1]
    scale = 20 / max(box.shape)
    size = (max(1, round(box.shape[1] * scale)), max(1, round(box.shape[0] * scale)))
    digit = np.asarray(Image.fromarray(np.uint8(box * 255)).resize(size, Image.Resampling.LANCZOS))
    canvas = np.zeros((28, 28), dtype=np.uint8)
    top, left = (28 - digit.shape[0]) // 2, (28 - digit.shape[1]) // 2
    canvas[top : top + digit.shape[0], left : left + digit.shape[1]] = digit
    return canvas


def classify(sketch: dict | None, framing: str):
    if sketch is None or sketch.get("composite") is None:
        return None, None
    drawing = ink(sketch)
    if drawing.max() <= 0.1:
        return None, None
    if framing == AS_MNIST:
        pixels = as_mnist(drawing)
    else:
        pixels = np.array(Image.fromarray(np.uint8(drawing * 255)).resize((28, 28), Image.Resampling.LANCZOS))
    with torch.no_grad():
        probabilities = model(to_input(torch.from_numpy(pixels)[None])).softmax(dim=1)[0]
    seen = Image.fromarray(pixels).resize((140, 140), Image.Resampling.NEAREST)
    return {str(digit): float(p) for digit, p in enumerate(probabilities)}, seen


with gr.Blocks(title="Digit sketch") as demo:
    gr.Markdown(
        "# Digit sketch\n"
        "Draw one digit. The model is the small CNN trained with affine augmentation in "
        "[experiment 003](https://github.com/hoshiori-dev/colab-template/tree/main/experiments/003-affine-augmentation). "
        f'Switch to "{AS_DRAWN}" and draw off-center, tilted or small to see how it copes with the shifts that '
        "experiment measured."
    )
    with gr.Row():
        with gr.Column():
            sketch = gr.Sketchpad(
                label="Your digit",
                type="numpy",
                canvas_size=(280, 280),
                brush=gr.Brush(colors=["#000000"], default_size=20),
                layers=False,
            )
            framing = gr.Radio([AS_MNIST, AS_DRAWN], value=AS_MNIST, label="Before the model sees it")
        with gr.Column():
            prediction = gr.Label(label="Prediction", num_top_classes=3)
            seen = gr.Image(label="What the model sees (28 by 28)", type="pil", interactive=False)
    sketch.change(classify, [sketch, framing], [prediction, seen])
    framing.change(classify, [sketch, framing], [prediction, seen])

if __name__ == "__main__":
    demo.launch()
