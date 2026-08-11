from __future__ import annotations

import numpy as np
from attune.vision.preprocessing.pipeline import PreprocessingConfig, Preprocessor
from attune.vision.preprocessing.transforms import denoise, normalize, resize, to_rgb


def test_resize_produces_target_dimensions() -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    resized = resize(frame, width=320, height=240)
    assert resized.shape == (240, 320, 3)


def test_to_rgb_swaps_blue_and_red_channels() -> None:
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    frame[:, :, 0] = 10  # B
    frame[:, :, 2] = 200  # R

    rgb = to_rgb(frame)

    assert (rgb[:, :, 0] == 200).all()  # R
    assert (rgb[:, :, 2] == 10).all()  # B


def test_normalize_scales_to_unit_range() -> None:
    frame = np.full((2, 2, 3), 255, dtype=np.uint8)
    normalized = normalize(frame)
    assert normalized.dtype == np.float32
    assert np.allclose(normalized, 1.0)


def test_preprocessor_resizes_and_converts_by_default() -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:, :, 2] = 200  # R channel in BGR

    processed = Preprocessor().process(frame)

    assert processed.shape == (480, 640, 3)  # default config target size
    assert (processed[:, :, 0] == 200).all()  # R now in position 0 after BGR->RGB


def test_preprocessor_honors_convert_to_rgb_false() -> None:
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    config = PreprocessingConfig(target_width=5, target_height=5, convert_to_rgb=False)

    processed = Preprocessor(config).process(frame)

    assert processed.shape == (5, 5, 3)


def _noisy_frame(base: int, noise_std: float, seed: int) -> np.ndarray:
    # Simulates the grainy sensor noise typical of low-light webcam frames:
    # a flat-color patch plus per-pixel Gaussian noise.
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, noise_std, size=(60, 60, 3))
    return np.clip(base + noise, 0, 255).astype(np.uint8)


def test_denoise_preserves_shape_and_dtype() -> None:
    frame = _noisy_frame(base=40, noise_std=25.0, seed=1)
    denoised = denoise(frame)
    assert denoised.shape == frame.shape
    assert denoised.dtype == frame.dtype


def test_denoise_reduces_noise_in_a_low_light_style_frame() -> None:
    # A dim (low-light), grainy frame — denoise() should smooth it out
    # without materially shifting its average brightness.
    frame = _noisy_frame(base=40, noise_std=25.0, seed=2)

    denoised = denoise(frame)

    assert float(np.std(denoised)) < float(np.std(frame))
    assert abs(float(np.mean(denoised)) - float(np.mean(frame))) < 5.0
