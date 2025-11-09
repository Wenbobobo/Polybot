from polybot.cli.commands import cmd_relayer_approve_usdc, cmd_relayer_approve_outcome


def test_relayer_approve_commands_fail_on_bad_private_key():
    out1 = cmd_relayer_approve_usdc(base_url="https://clob.polymarket.com", private_key="bad", amount=100.0)
    assert "invalid private_key" in out1
    out2 = cmd_relayer_approve_outcome(base_url="https://clob.polymarket.com", private_key="bad", token_address="0xabc", amount=10.0)
    assert "invalid private_key" in out2
