from pathlib import Path

from polybot.service.config import load_service_config


def test_service_config_reads_relayer_signer_options(tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "real"
        base_url = "https://clob.polymarket.com"
        dry_run = true
        private_key = "0xabc"
        chain_id = 137
        timeout_s = 7.5
        """,
        encoding="utf-8",
    )
    sc = load_service_config(str(cfg))
    assert sc.relayer_chain_id == 137
    assert abs(sc.relayer_timeout_s - 7.5) < 1e-9

