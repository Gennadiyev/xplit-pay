from . import XplitLog, XPLIT_VERSION
from mdutils.mdutils import MdUtils
from mdutils import Html
from datetime import datetime


def compute_stats(xplit_log: XplitLog) -> dict:
    stats = {}
    stats["total"] = 0
    stats["total_expenses"] = {}
    stats["total_paid"] = {}
    for entry in xplit_log.entries:
        stats["total"] += entry.expense
        if entry.paid_by not in stats["total_paid"]:
            stats["total_paid"][entry.paid_by] = 0
        stats["total_paid"][entry.paid_by] += entry.expense
        for person, amount in entry.splits.items():
            if person not in stats["total_expenses"]:
                stats["total_expenses"][person] = 0
            stats["total_expenses"][person] += amount
    stats["balance"] = {}
    for person in stats["total_expenses"]:
        stats["balance"][person] = (
            stats["total_paid"][person] - stats["total_expenses"][person]
        )
    for entry in xplit_log.extra_payments:
        if entry[0] not in stats["balance"]:
            stats["balance"][entry[0]] = 0
        if entry[1] not in stats["balance"]:
            stats["balance"][entry[1]] = 0
        stats["balance"][entry[0]] += entry[2]
        stats["balance"][entry[1]] -= entry[2]
    return stats


def _generate_markdown_zh_cn(xplit_log: XplitLog, md_path: str, stats: dict):
    md_file = MdUtils(file_name=md_path)

    # Add Title
    md_file.new_header(level=1, title=xplit_log.title)

    # Add Description
    for line in xplit_log.description.split("\n"):
        md_file.new_paragraph(f"> {line}")

    # Add Stats
    md_file.new_header(level=2, title="统计与结算")
    md_file.new_paragraph(f"**结算货币**：{xplit_log.currency_main}")
    md_file.new_paragraph(f"**总支出** {stats['total']:.2f}")
    text_list = ["人员", "实际花费", "实际支付", "额外盈亏补偿"]
    people = list(stats["total_expenses"].keys())
    for person in people:
        text_list.extend(
            [
                person,
                f"{stats['total_expenses'][person]:.2f}",
                f"{stats['total_paid'][person]:.2f}",
                f"{stats['balance'][person]:.2f}",
            ]
        )
    md_file.new_table(columns=4, rows=len(people) + 1, text=text_list)

    # Entries
    # First perform a group & sort. Within the same section, sort by time
    current_subtitle = None
    all_entries = []
    current_section_entries = []
    for entry in xplit_log.entries:
        if current_subtitle != entry.section_title:
            current_subtitle = entry.section_title
            if current_section_entries:
                all_entries.extend(
                    sorted(
                        current_section_entries,
                        key=lambda x: x.time if x.time is not None else datetime.now(),
                    )
                )
            current_section_entries = []
        current_section_entries.append(entry)
    if current_section_entries:
        all_entries.extend(
            sorted(
                current_section_entries,
                key=lambda x: x.time if x.time is not None else datetime.now(),
            )
        )
    # Write to markdown
    current_subtitle = None
    for entry in all_entries:
        if current_subtitle != entry.section_title:
            md_file.new_header(level=2, title=entry.section_title)
            current_subtitle = entry.section_title
        md_file.new_header(level=3, title=entry.title)
        md_file.new_paragraph("> " + entry.description)
        md_file.new_paragraph(
            f"**支出**：{entry.expense:.2f} ({entry.paid_by}) | 🕒 {entry.time.strftime('%m/%d %H:%M') if entry.time is not None else '-'}"
        )
        people = list(entry.splits.keys())
        amounts = list(entry.splits.values())
        # Sort by people
        people, amounts = zip(*sorted(zip(people, amounts)))
        people = list(people)
        amounts_str = [f"{amount:.2f}" for amount in amounts]
        text_list = people + amounts_str
        md_file.new_table(columns=len(people), rows=2, text=text_list)

    # Additional Items, Balances, and Metadata (placeholders for now)
    md_file.new_header(level=2, title="附加项")
    extra_payments = xplit_log.extra_payments
    if extra_payments:
        text_list = ["付款人", "收款人", "金额"]
        for payment in extra_payments:
            text_list.extend([payment[0], payment[1], f"{payment[2]:.2f}"])
        md_file.new_table(columns=3, rows=len(extra_payments) + 1, text=text_list)

    # Developer Information
    md_file.new_header(level=2, title="开发者相关")
    md_file.new_paragraph(f"XplitPay 版本：`{XPLIT_VERSION}`")
    md_file.new_paragraph(f"生成时间：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    md_file.new_paragraph(f"源数据：\n\n```plaintext\n{xplit_log.original_content}\n```")

    # Save the markdown file
    md_file.create_md_file()


def _generate_markdown_en(xplit_log: XplitLog, md_path: str, stats: dict):
    md_file = MdUtils(file_name=md_path)

    # Add Title
    md_file.new_header(level=1, title=xplit_log.title)

    # Add Description
    for line in xplit_log.description.split("\n"):
        md_file.new_paragraph(f"> {line}")

    # Add Stats
    md_file.new_header(level=2, title="Stats")
    md_file.new_paragraph(f"**Using currency:** {xplit_log.currency_main}")
    md_file.new_paragraph(f"**Total Expenditure:** {stats['total']:.2f}")
    text_list = ["Person", "Actual Expense", "Amount Paid", "Should Receive..."]
    people = list(stats["total_expenses"].keys())
    for person in people:
        text_list.extend(
            [
                person,
                f"{stats['total_expenses'][person]:.2f}",
                f"{stats['total_paid'][person]:.2f}",
                f"{stats['balance'][person]:.2f}",
            ]
        )
    md_file.new_table(columns=4, rows=len(people) + 1, text=text_list)

    # Entries
    # First perform a group & sort. Within the same section, sort by time
    current_subtitle = None
    all_entries = []
    current_section_entries = []
    for entry in xplit_log.entries:
        if current_subtitle != entry.section_title:
            current_subtitle = entry.section_title
            if current_section_entries:
                all_entries.extend(
                    sorted(
                        current_section_entries,
                        key=lambda x: x.time if x.time is not None else datetime.now(),
                    )
                )
            current_section_entries = []
        current_section_entries.append(entry)
    if current_section_entries:
        all_entries.extend(
            sorted(
                current_section_entries,
                key=lambda x: x.time if x.time is not None else datetime.now(),
            )
        )
    # Write to markdown
    current_subtitle = None
    for entry in all_entries:
        if current_subtitle != entry.section_title:
            md_file.new_header(level=2, title=entry.section_title)
            current_subtitle = entry.section_title
        md_file.new_header(level=3, title=entry.title)
        md_file.new_paragraph("> " + entry.description)
        md_file.new_paragraph(
            f"**{entry.expense:.2f}** spent | paid by {entry.paid_by} {'at ' + entry.time.strftime('%m/%d %H:%M') if entry.time is not None else ''}"
        )
        people = list(entry.splits.keys())
        amounts = list(entry.splits.values())
        # Sort by people
        people, amounts = zip(*sorted(zip(people, amounts)))
        people = list(people)
        amounts_str = [f"{amount:.2f}" for amount in amounts]
        text_list = people + amounts_str
        md_file.new_table(columns=len(people), rows=2, text=text_list)

    # Additional Items, Balances, and Metadata (placeholders for now)
    md_file.new_header(level=2, title="Extra Payments")
    extra_payments = xplit_log.extra_payments
    if extra_payments:
        text_list = ["From", "To", "Amount"]
        for payment in extra_payments:
            text_list.extend([payment[0], payment[1], f"{payment[2]:.2f}"])
        md_file.new_table(columns=3, rows=len(extra_payments) + 1, text=text_list)

    # Developer Information
    md_file.new_header(level=2, title="Developer Info")
    md_file.new_paragraph(f"XplitPay v`{XPLIT_VERSION}`")
    md_file.new_paragraph(
        f"Generated at `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    md_file.new_paragraph(f"Source:\n\n```plaintext\n{xplit_log.original_content}\n```")

    # Save the markdown file
    md_file.create_md_file()


def generate_markdown(xplit_log: XplitLog, md_path: str, locale: str = "zh_CN"):
    stats = compute_stats(xplit_log)

    if locale == "zh_CN":
        _generate_markdown_zh_cn(xplit_log, md_path, stats)
    elif locale == "en":
        _generate_markdown_en(xplit_log, md_path, stats)
