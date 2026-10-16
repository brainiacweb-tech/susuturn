"""Command-line interface and dispatch for SusuTurn."""

import argparse
import sys
from pathlib import Path

from susuturn.database import get_connection, init_db, DEFAULT_DB_PATH
from susuturn.exceptions import SusuTurnError, WeekClosingBlockedError
from susuturn.money import format_pesewas_to_ghs
from susuturn.reports import format_closing_blocked, format_closing_success, format_group_report
from susuturn.service import SusuService


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="susuturn",
        description="SusuTurn — Rotating Savings Group Management System (Ghanaian Susu Model)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m susuturn create --name \"KNUST Friends Susu\" --weekly 50.00\n"
            "  python -m susuturn add-member --name \"Ama\"\n"
            "  python -m susuturn contribute --member \"Ama\" --amount 50.00\n"
            "  python -m susuturn close-week\n"
            "  python -m susuturn report\n"
        ),
    )

    parser.add_argument(
        "--db",
        type=str,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database file (default: {DEFAULT_DB_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: create
    create_parser = subparsers.add_parser("create", help="Create a new rotating savings group")
    create_parser.add_argument("--name", required=True, type=str, help="Group name")
    create_parser.add_argument("--weekly", required=True, type=str, help="Fixed weekly contribution (e.g. 50.00)")

    # Command: add-member
    member_parser = subparsers.add_parser("add-member", help="Register a new member")
    member_parser.add_argument("--name", required=True, type=str, help="Unique member name")

    # Command: contribute
    contrib_parser = subparsers.add_parser("contribute", help="Record a weekly contribution")
    contrib_parser.add_argument("--member", required=True, type=str, help="Member name")
    contrib_parser.add_argument("--amount", required=True, type=str, help="Contribution amount (e.g. 50.00 or 20.00)")

    # Command: close-week
    subparsers.add_parser("close-week", help="Validate contributions, pay pot, and advance to next week")

    # Command: report
    subparsers.add_parser("report", help="Display full savings group status, contributions, and payout history")

    return parser


def handle_create(service: SusuService, args: argparse.Namespace) -> int:
    group = service.create_group(name=args.name, weekly_amount=args.weekly)
    amount_str = format_pesewas_to_ghs(group.weekly_contribution_pesewas)
    print(f"Savings group '{group.name}' created successfully.")
    print(f"Weekly contribution: {amount_str}")
    return 0


def handle_add_member(service: SusuService, args: argparse.Namespace) -> int:
    member = service.add_member(name=args.name)
    print(f"Member '{member.name}' registered successfully.")
    print(f"Joining Position: #{member.joining_position} (Payout Week: {member.joining_position})")
    return 0


def handle_contribute(service: SusuService, args: argparse.Namespace) -> int:
    contrib = service.record_contribution(member_name=args.member, amount=args.amount)
    group = service.get_group()
    member = service.repo.get_member_by_name(args.member)
    already_paid = service.repo.get_member_contributed_amount(contrib.member_id, group.current_week)
    balance = group.weekly_contribution_pesewas - already_paid

    amt_str = format_pesewas_to_ghs(contrib.amount_pesewas)
    paid_str = format_pesewas_to_ghs(already_paid)
    bal_str = format_pesewas_to_ghs(balance)

    print(f"Payment of {amt_str} recorded for {member.name if member else args.member} (Week {contrib.week_number}).")
    print(f"Total contributed this week: {paid_str}")
    if balance > 0:
        print(f"Remaining balance: {bal_str}")
    else:
        print("Weekly contribution complete: PAID IN FULL")
    return 0


def handle_close_week(service: SusuService, args: argparse.Namespace) -> int:
    try:
        closing_info = service.close_week()
        print(format_closing_success(closing_info))
        return 0
    except WeekClosingBlockedError as e:
        if e.outstanding_members:
            group = service.get_group()
            print(format_closing_blocked(group.current_week, e.outstanding_members))
            return 1
        else:
            print(f"Error: {e}", file=sys.stderr)
            return 1


def handle_report(service: SusuService, args: argparse.Namespace) -> int:
    data = service.get_group_report_data()
    print(format_group_report(data))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI execution entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        conn = get_connection(args.db)
        init_db(conn)
        service = SusuService(conn)

        if args.command == "create":
            return handle_create(service, args)
        elif args.command == "add-member":
            return handle_add_member(service, args)
        elif args.command == "contribute":
            return handle_contribute(service, args)
        elif args.command == "close-week":
            return handle_close_week(service, args)
        elif args.command == "report":
            return handle_report(service, args)
        else:
            parser.print_help()
            return 1
    except SusuTurnError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
