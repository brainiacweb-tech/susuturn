"""End-to-end command-line interface tests."""

import pytest
from susuturn.cli import main


class TestCLI:
    """CLI tests running against temporary SQLite databases."""

    def test_cli_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "SusuTurn" in captured.out
        assert "create" in captured.out
        assert "add-member" in captured.out

    def test_cli_no_args_shows_help(self, capsys):
        code = main([])
        assert code == 0
        captured = capsys.readouterr()
        assert "SusuTurn" in captured.out
        assert "create" in captured.out

    def test_cli_lifecycle(self, tmp_path, capsys):
        db_path = str(tmp_path / "test_susu.db")

        # 1. Create group
        assert main(["--db", db_path, "create", "--name", "KNUST Friends Susu", "--weekly", "50.00"]) == 0
        out1 = capsys.readouterr().out
        assert "created successfully" in out1

        # 2. Add members
        assert main(["--db", db_path, "add-member", "--name", "Ama"]) == 0
        assert main(["--db", db_path, "add-member", "--name", "Kofi"]) == 0
        assert main(["--db", db_path, "add-member", "--name", "Esi"]) == 0
        out2 = capsys.readouterr().out
        assert "registered successfully" in out2

        # 3. Partial payments
        assert main(["--db", db_path, "contribute", "--member", "Ama", "--amount", "50.00"]) == 0
        assert main(["--db", db_path, "contribute", "--member", "Kofi", "--amount", "50.00"]) == 0
        assert main(["--db", db_path, "contribute", "--member", "Esi", "--amount", "30.00"]) == 0

        # 4. Attempt to close week (should fail because Esi owes 20.00)
        assert main(["--db", db_path, "close-week"]) == 1
        out_blocked = capsys.readouterr().out
        assert "CANNOT CLOSE WEEK" in out_blocked
        assert "Esi owes GHS 20.00" in out_blocked

        # 5. Complete payment for Esi
        assert main(["--db", db_path, "contribute", "--member", "Esi", "--amount", "20.00"]) == 0
        assert main(["--db", db_path, "close-week"]) == 0
        out_closed = capsys.readouterr().out
        assert "Week 1 successfully closed." in out_closed
        assert "Payout recipient: Ama" in out_closed
        assert "Week 2 is now active." in out_closed
        assert "Next recipient: Kofi" in out_closed

        # 6. View report
        assert main(["--db", db_path, "report"]) == 0
        out_report = capsys.readouterr().out
        assert "SUSUTURN GROUP REPORT" in out_report
        assert "KNUST Friends Susu" in out_report
        assert "Current Week:        Week 2" in out_report

    def test_cli_duplicate_group_error(self, tmp_path, capsys):
        db_path = str(tmp_path / "test_dup.db")
        assert main(["--db", db_path, "create", "--name", "First", "--weekly", "50.00"]) == 0
        assert main(["--db", db_path, "create", "--name", "Second", "--weekly", "50.00"]) == 1
        err = capsys.readouterr().err
        assert "already exists" in err

    def test_cli_invalid_money_error(self, tmp_path, capsys):
        db_path = str(tmp_path / "test_money.db")
        assert main(["--db", db_path, "create", "--name", "Invalid", "--weekly", "50.123"]) == 1
        err = capsys.readouterr().err
        assert "more than 2 decimal places" in err
