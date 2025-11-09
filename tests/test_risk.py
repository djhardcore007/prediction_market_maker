from src.risk.limits import Limits
from src.risk.kill_switch import KillSwitch
from src.risk.exposure import delta_binary


def test_limits():
    limits = Limits(max_notional=1000, per_market_max_position=100)
    assert limits.within_notional(999)
    assert not limits.within_notional(1001)
    assert limits.within_position(50)
    assert not limits.within_position(150)


def test_kill_switch():
    ks = KillSwitch(max_loss=100)
    assert not ks.check(unrealized_pnl=-50)
    assert ks.check(unrealized_pnl=-100)


def test_delta_binary():
    assert delta_binary(0.6, 10) == 10
