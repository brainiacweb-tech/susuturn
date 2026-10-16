"""Unit tests for report generation formatting and accuracy."""

from susuturn.reports import format_group_report, format_closing_blocked, format_closing_success


class TestReports:
    """Tests covering report formatting for various cycle stages."""

    def test_report_empty_group(self, service):
        service.create_group("New Group", "50.00")
        data = service.get_group_report_data()
        report = format_group_report(data)

        assert "New Group" in report
        assert "GHS 50.00" in report
        assert "Total Members:       0" in report
        assert "Cycle Status:        ACTIVE" in report
        assert "No members registered yet." in report
        assert "No payouts recorded yet." in report

    def test_report_active_group_with_partial_contributions(self, sample_group):
        service = sample_group["service"]
        service.record_contribution("Ama", "50.00")
        service.record_contribution("Kofi", "20.00")
        # Esi paid 0

        data = service.get_group_report_data()
        report = format_group_report(data)

        assert "KNUST Friends Susu" in report
        assert "Total Members:       3" in report
        assert "Total Weekly Pot:    GHS 150.00" in report
        assert "Current Week:        Week 1" in report
        assert "Ama" in report
        assert "PAID" in report
        assert "OWING" in report
        assert "Next scheduled recipient: Ama (Week 1)" in report

    def test_report_completed_cycle(self, sample_group):
        service = sample_group["service"]
        # Complete full cycle of 3 weeks
        for _ in range(3):
            service.record_contribution("Ama", "50.00")
            service.record_contribution("Kofi", "50.00")
            service.record_contribution("Esi", "50.00")
            service.close_week()

        data = service.get_group_report_data()
        report = format_group_report(data)

        assert "Cycle Status:        COMPLETED" in report
        assert "Active Week:         None (Cycle Finished)" in report
        assert "SAVINGS CYCLE COMPLETED" in report or "Cycle completed" in report
        assert "Week 1" in report or "1      Ama" in report
        assert "2      Kofi" in report
        assert "3      Esi" in report

    def test_format_closing_blocked(self):
        msg = format_closing_blocked(1, [{"name": "Esi", "balance_formatted": "GHS 20.00"}])
        assert "CANNOT CLOSE WEEK" in msg
        assert "- Esi owes GHS 20.00" in msg
        assert "Payout: BLOCKED" in msg
        assert "Current week remains: 1" in msg

    def test_format_closing_success(self):
        info = {
            "closed_week": 1,
            "total_pot_pesewas": 15000,
            "recipient_name": "Ama",
            "is_cycle_completed": False,
            "next_week": 2,
            "next_recipient": "Kofi",
        }
        msg = format_closing_success(info)
        assert "All members have paid in full." in msg
        assert "Total pot: GHS 150.00" in msg
        assert "Payout recipient: Ama" in msg
        assert "Week 1 successfully closed." in msg
        assert "Week 2 is now active." in msg
        assert "Next recipient: Kofi" in msg
