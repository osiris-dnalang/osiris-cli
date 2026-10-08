"""The core's architecture is chosen per checkpoint folder (arch.json), never by accident.

NCLM-ARCH-1 trains a "standard" arm beside the live "crsm" core. The live folder has no arch.json and
must build exactly the core it always built; a checkpoint of one architecture must never be half-loaded
into the other (copying by index used to overwrite the leading tensors before failing).
"""
import json

import numpy as np
import pytest

from osiris_cli import osiris_repl

otc = osiris_repl.otc
pytestmark = pytest.mark.skipif(otc is None, reason="osiris_termux_console not importable")


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(otc, "ORGANISM_HOME", str(tmp_path))
    return tmp_path


def test_a_folder_without_arch_json_builds_the_live_core_unchanged(home):
    from osiris.nclm import SovereignBlock
    from osiris.nclm.positions import phase_conjugate_positional_encoding

    model, _ = otc._organism_build()
    assert otc._organism_arch() == "crsm" and model.organism_arch == "crsm"
    assert model.num_parameters() == 726_304
    assert all(isinstance(b, SovereignBlock) for b in model.blocks)
    cfg = model.config
    assert (cfg.torsion_lock, cfg.phase_conjugate, cfg.fractal_embedding, cfg.positional) == (True, True, False, "phi")
    assert (cfg.dim, cfg.n_layers, cfg.n_heads, cfg.ff_dim, cfg.max_seq_len, cfg.dropout) == (128, 4, 4, 256, 128, 0.0)
    np.testing.assert_array_equal(model.pos_enc.data, phase_conjugate_positional_encoding(128, 128).data)


def test_the_standard_arm_is_plain_and_the_same_size(home):
    from osiris.nclm.positions import standard_sinusoidal_positional_encoding
    from osiris.nclm.transformer import TransformerBlock

    (home / "arch.json").write_text(json.dumps({"arch": "standard"}))
    model, _ = otc._organism_build()
    assert model.organism_arch == "standard" and model.num_parameters() == 725_760
    assert all(isinstance(b, TransformerBlock) for b in model.blocks)
    assert not model.config.pilot_wave and not model.config.golden_scale and model.config.ff_dim == 384
    np.testing.assert_array_equal(model.pos_enc.data, standard_sinusoidal_positional_encoding(128, 128).data)


def test_an_unknown_arch_is_an_error_not_a_fallback(home):
    (home / "arch.json").write_text(json.dumps({"arch": "quantum"}))
    with pytest.raises(ValueError, match="unknown architecture"):
        otc._organism_arch()


def test_a_checkpoint_of_another_architecture_leaves_the_model_untouched(home, capsys):
    np.random.seed(3)
    standard, sopt = otc._organism_build("standard")
    otc._organism_save(standard, sopt, 7, [1.0], rotate=False)
    np.random.seed(4)
    crsm, copt = otc._organism_build("crsm")
    before = [p.data.copy() for p in crsm.parameters()]
    assert otc._organism_load(crsm, copt) == (0, [])
    assert "starting fresh" in capsys.readouterr().out
    assert all(np.array_equal(a, p.data) for a, p in zip(before, crsm.parameters()))


def test_a_checkpoint_round_trips_into_its_own_architecture(home):
    (home / "arch.json").write_text(json.dumps({"arch": "standard"}))
    np.random.seed(5)
    model, opt = otc._organism_build()
    otc._organism_save(model, opt, 11, [2.0], rotate=False)
    again, aopt = otc._organism_build()
    assert otc._organism_load(again, aopt)[0] == 11
    assert all(np.array_equal(a.data, b.data) for a, b in zip(model.parameters(), again.parameters()))
