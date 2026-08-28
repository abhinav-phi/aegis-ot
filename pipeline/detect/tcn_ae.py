"""TCN-AE: dilated causal-conv autoencoder with per-channel residuals (DET-01).

Deterministic CPU path (R-ML-10). Attribution-ready: residual per channel is
the mean absolute reconstruction error over the window.
"""
from __future__ import annotations

import numpy as np

try:
    import torch
    from torch import nn

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False


def _build(n_sensors: int, W: int, channels: int = 32, latent: int = 8):
    if not TORCH_AVAILABLE:
        raise ImportError("torch_not_installed")
    pad = lambda d, k=3: d * (k - 1)  # causal: pad left only

    class CausalBlock(nn.Module):
        def __init__(self, cin, cout, dilation):
            super().__init__()
            self.pad = pad(dilation)
            self.conv = nn.Conv1d(cin, cout, 3, dilation=dilation)

        def forward(self, x):
            return self.conv(nn.functional.pad(x, (self.pad, 0)))

    class TCNAE(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = nn.Sequential(
                CausalBlock(n_sensors, channels, 1), nn.ReLU(),
                CausalBlock(channels, channels, 2), nn.ReLU(),
                CausalBlock(channels, latent, 4), nn.ReLU(),
            )
            self.dec = nn.Sequential(
                CausalBlock(latent, channels, 4), nn.ReLU(),
                CausalBlock(channels, channels, 2), nn.ReLU(),
                CausalBlock(channels, n_sensors, 1),
            )

        def forward(self, x):  # x: [B, S, T] -> reconstruct same shape
            # Conv1d consumes (B, C=S, T) directly — callers already deliver
            # [B, S, T]; the previous extra transpose swapped S↔T and made
            # every forward pass a channel-count mismatch.
            z = self.enc(x)
            r = self.dec(z)
            return r

    return TCNAE()


class TCNAEDetector:
    family = "tcn_ae"

    def __init__(self, n_sensors: int, W: int, seed: int = 0):
        self.n_sensors, self.W, self.seed = n_sensors, W, seed
        self.residual_scale = np.ones(n_sensors, dtype=np.float64)
        self.torch = None
        self.net = None
        if TORCH_AVAILABLE:
            torch.manual_seed(seed)
            self.torch = torch
            self.net = _build(n_sensors, W)

    def fit(self, train_windows: np.ndarray, epochs: int = 30,
            batch: int = 64, lr: float = 1e-3) -> list[float]:
        if not TORCH_AVAILABLE:
            raise ImportError("torch_not_installed")
        t = self.torch
        ds = t.tensor(train_windows.transpose(0, 2, 1), dtype=t.float32)
        opt = t.optim.Adam(self.net.parameters(), lr=lr)
        loss_fn = nn.MSELoss()
        losses: list[float] = []
        for _ in range(epochs):
            perm = t.randperm(len(ds))
            for i in range(0, len(ds), batch):
                idx = perm[i:i + batch]
                x = ds[idx]
                opt.zero_grad()
                recon = self.net(x)
                loss = loss_fn(recon, x)
                loss.backward()
                opt.step()
            losses.append(float(loss.item()))
        self._fit_residual_scale(train_windows)
        return losses

    @torch.no_grad() if TORCH_AVAILABLE else (lambda f: f)  # type: ignore[misc]
    def _residuals(self, windows: np.ndarray) -> np.ndarray:
        """Per-window, per-sensor mean |error| — attribution input."""
        if not TORCH_AVAILABLE:
            raise ImportError("torch_not_installed")
        t = self.torch
        with t.no_grad():
            x_np = windows.transpose(0, 2, 1)                     # [N,S,T]
            x = t.tensor(x_np, dtype=t.float32)
            recon = self.net(x).numpy()                           # [N,S,T]
        return np.abs(x_np - recon).mean(axis=1)  # [N, S]

    def _fit_residual_scale(self, train_windows: np.ndarray) -> None:
        res = self._residuals(train_windows[:512])
        std = res.std(axis=0)
        self.residual_scale = np.where(std > 1e-9, std, 1.0)

    def score_and_contribute(self, windows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Returns (window scores, per-sensor mean residuals). R-ML-07 safe."""
        res = self._residuals(windows) / self.residual_scale
        scores = res.mean(axis=1)
        return scores.astype(np.float64), res.astype(np.float64)

    def save_bytes(self) -> bytes:
        import io

        buf = io.BytesIO()
        payload = {
            "n_sensors": self.n_sensors, "W": self.W, "seed": self.seed,
            "residual_scale": self.residual_scale.tolist(),
            "state": self.net.state_dict(),
        }
        self.torch.save(payload, buf)
        return buf.getvalue()

    @classmethod
    def load_bytes(cls, data: bytes) -> TCNAEDetector:
        import io

        if not TORCH_AVAILABLE:
            raise ImportError("torch_not_installed")
        buf = io.BytesIO(data)
        payload = torch.load(buf, map_location="cpu", weights_only=False)
        det = cls(payload["n_sensors"], payload["W"], payload["seed"])
        det.net.load_state_dict(payload["state"])
        det.residual_scale = np.asarray(payload["residual_scale"])
        return det
