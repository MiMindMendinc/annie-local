from annie.core.speed_kernel import SpeedKernelAdapter


def test_speed_kernel_disabled_by_default():
    status = SpeedKernelAdapter().status()

    assert status.enabled is False
    assert status.backend == "dominus-ultra"
    assert status.mode == "disabled"


def test_speed_kernel_metadata_shape():
    data = SpeedKernelAdapter(enabled=True).metadata()

    assert set(data) == {"enabled", "available", "backend", "mode", "note"}
    assert data["enabled"] is True
    assert data["backend"] == "dominus-ultra"
