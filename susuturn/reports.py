"""Terminal report generators and text formatters for SusuTurn."""

from susuturn.money import format_pesewas_to_ghs


def format_closing_blocked(week_number: int, outstanding: list[dict]) -> str:
    """Format the message displayed when week closing is blocked by unpaid contributions."""
    lines = [
        f"SUSUTURN - WEEK {week_number} CLOSING",
        "",
        "Status: CANNOT CLOSE WEEK",
        "",
        "Outstanding contributions:",
    ]
    for item in outstanding:
        lines.append(f"- {item['name']} owes {item['balance_formatted']}")

    lines.extend([
        "",
        "Payout: BLOCKED",
        f"Current week remains: {week_number}",
    ])
    return "\n".join(lines)


def format_closing_success(closing_info: dict) -> str:
    """Format the message displayed when a week closes successfully."""
    week = closing_info["closed_week"]
    pot_str = format_pesewas_to_ghs(closing_info["total_pot_pesewas"])
    recipient = closing_info["recipient_name"]

    lines = [
        f"SUSUTURN - WEEK {week} CLOSING",
        "",
        "All members have paid in full.",
        "",
        f"Total pot: {pot_str}",
        f"Payout recipient: {recipient}",
        f"Payout amount: {pot_str}",
        "",
        f"Week {week} successfully closed.",
    ]

    if closing_info["is_cycle_completed"]:
        lines.extend([
            "",
            "============================================================",
            "SAVINGS CYCLE COMPLETED!",
            "All registered members have received their scheduled payout.",
            "============================================================",
        ])
    else:
        lines.extend([
            f"Week {closing_info['next_week']} is now active.",
            f"Next recipient: {closing_info['next_recipient']}",
        ])

    return "\n".join(lines)


def format_group_report(report_data: dict) -> str:
    """Format the comprehensive group report."""
    group = report_data["group"]
    total_members = report_data["total_members"]
    total_pot = format_pesewas_to_ghs(report_data["total_pot_pesewas"])
    weekly_str = format_pesewas_to_ghs(group.weekly_contribution_pesewas)
    cycle_status = "COMPLETED" if group.is_completed else "ACTIVE"

    lines = [
        "============================================================",
        "                    SUSUTURN GROUP REPORT                   ",
        "============================================================",
        "",
        "GROUP SUMMARY",
        "-------------",
        f"Group Name:          {group.name}",
        f"Weekly Contribution: {weekly_str}",
        f"Total Members:       {total_members}",
        f"Cycle Status:        {cycle_status}",
    ]

    if group.is_completed:
        lines.append("Active Week:         None (Cycle Finished)")
    else:
        lines.append(f"Current Week:        Week {group.current_week}")
    lines.append(f"Total Weekly Pot:    {total_pot}")
    lines.append("")

    # Member Contribution Section
    lines.extend([
        "MEMBER CONTRIBUTION REPORT",
        "--------------------------",
    ])

    if group.is_completed:
        lines.append("All scheduled contributions and payouts for this cycle are complete.")
        lines.append("")
    elif not report_data["member_statuses"]:
        lines.append("No members registered yet.")
        lines.append("")
    else:
        header = f"{'Pos':<5} {'Member Name':<20} {'Contributed':<15} {'Outstanding':<15} {'Status':<10}"
        lines.append(header)
        lines.append("-" * len(header))
        for s in report_data["member_statuses"]:
            paid_str = format_pesewas_to_ghs(s.paid_pesewas)
            balance_str = format_pesewas_to_ghs(s.balance_pesewas)
            status_str = "PAID" if s.is_paid_in_full else "OWING"
            lines.append(
                f"{s.joining_position:<5} {s.member_name:<20} {paid_str:<15} {balance_str:<15} {status_str:<10}"
            )
        lines.append("")

    # Payout History Section
    lines.extend([
        "PAYOUT HISTORY",
        "--------------",
    ])
    payouts = report_data["payouts"]
    if not payouts:
        lines.append("No payouts recorded yet.")
        lines.append("")
    else:
        p_header = f"{'Week':<6} {'Recipient':<20} {'Amount':<15} {'Date (UTC)':<20}"
        lines.append(p_header)
        lines.append("-" * len(p_header))
        for p in payouts:
            amt_str = format_pesewas_to_ghs(p.amount_pesewas)
            lines.append(f"{p.week_number:<6} {p.recipient_name:<20} {amt_str:<15} {p.created_at:<20}")
        lines.append("")

    # Upcoming Payout Section
    lines.extend([
        "UPCOMING PAYOUT",
        "---------------",
    ])
    if group.is_completed:
        lines.append("Cycle completed. No upcoming payouts.")
    elif report_data["next_recipient"]:
        lines.append(f"Next scheduled recipient: {report_data['next_recipient']} (Week {group.current_week})")
    else:
        lines.append("Next scheduled recipient: Pending member registration.")

    lines.append("============================================================")
    return "\n".join(lines)
