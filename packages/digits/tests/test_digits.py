import numpy as np
import torch
from datasets import Dataset, Features, Image, Value
from PIL import Image as PILImage

from digits import SmallCNN, accuracy, load_arrays, load_weights, save_arrays, save_weights, to_input
from digits.data import MEAN, STD, dataset_to_arrays


def fake_digits(count: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, size=(count, 28, 28), dtype=np.uint8), rng.integers(0, 10, size=count)


def test_hub_rows_become_uint8_images_and_int_labels():
    images, labels = fake_digits(3)
    dataset = Dataset.from_dict(
        {"image": [PILImage.fromarray(image) for image in images], "label": labels.tolist()},
        features=Features({"image": Image(), "label": Value("int64")}),
    )
    loaded_images, loaded_labels = dataset_to_arrays(dataset)
    assert loaded_images.dtype == np.uint8 and loaded_labels.dtype == np.int64
    np.testing.assert_array_equal(loaded_images, images)
    np.testing.assert_array_equal(loaded_labels, labels)


def test_arrays_survive_a_round_trip_through_a_file(tmp_path):
    images, labels = fake_digits(5)
    save_arrays(tmp_path / "set.npz", images, labels)
    loaded_images, loaded_labels = load_arrays(tmp_path / "set.npz")
    np.testing.assert_array_equal(loaded_images, images)
    np.testing.assert_array_equal(loaded_labels, labels)


def test_to_input_normalizes_and_adds_a_channel():
    images = np.array([np.zeros((28, 28)), np.full((28, 28), 255)], dtype=np.uint8)
    batch = to_input(images)
    assert batch.shape == (2, 1, 28, 28)
    assert torch.allclose(batch[0], torch.tensor(-MEAN / STD))
    assert torch.allclose(batch[1], torch.tensor((1 - MEAN) / STD))


def test_model_maps_a_batch_to_ten_logits():
    images, _ = fake_digits(4)
    assert SmallCNN()(to_input(images)).shape == (4, 10)


def test_accuracy_counts_matches_across_batches():
    images, _ = fake_digits(7)
    model = SmallCNN()
    with torch.no_grad():
        predicted = model.eval()(to_input(images)).argmax(dim=1).numpy()
    wrong = (predicted + 1) % 10
    assert accuracy(model, images, predicted, batch_size=3) == 1.0
    assert accuracy(model, images, wrong, batch_size=3) == 0.0


def test_saved_weights_reproduce_the_model(tmp_path):
    images, _ = fake_digits(4)
    model = SmallCNN().eval()
    save_weights(model, tmp_path / "model.safetensors")
    restored = load_weights(tmp_path / "model.safetensors")
    with torch.no_grad():
        assert torch.equal(model(to_input(images)), restored(to_input(images)))
