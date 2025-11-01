from polybot.cli.commands import cmd_relayer_approve_usdc, cmd_relayer_approve_outcome


def test_relayer_approve_commands_print_friendly_message_when_unavailable():
    out1 = cmd_relayer_approve_usdc(base_url="https://clob.polymarket.com", private_key="0xk", amount=100.0)
    assert out1.startswith("relayer unavailable:") or out1.startswith("not implemented:")
    out2 = cmd_relayer_approve_outcome(base_url="https://clob.polymarket.com", private_key="0xk", token_address="0xabc", amount=10.0)
    assert out2.startswith("relayer unavailable:") or out2.startswith("not implemented:")

