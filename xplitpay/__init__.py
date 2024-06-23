"""XplitPay

XplitPay is a simple python library that helps you split payments between multiple people.

@author: Kunologist
"""
import re
from pathlib import Path
from typing import Union, List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger

XPLIT_VERSION = '0.0.3'

@dataclass
class XplitEntry:
    section_title: str
    title: str
    description: str
    time: Optional[datetime]
    paid_by: str
    payment_method: str
    expense: float
    splits: Dict[str, float]

@dataclass
class XplitLog:
    version: str
    title: str
    author: str
    people: Dict[str, str]
    currencies: Dict[str, Union[str, Tuple[str, float]]]
    currency_main: str
    payment_methods: Dict[str, str]
    description: str
    entries: List[XplitEntry] = field(default_factory=list)
    extra_payments: List[Tuple[str, str, float]] = field(default_factory=list)
    original_content: str = None

def uncomment_line(line: str) -> str:
    if '#' in line:
        parts = line.split('#', 1)
        uncommented = parts[0].strip() + (f' #{parts[1].strip()}' if parts[1].strip() else '')
    else:
        uncommented = line.strip()
    return uncommented

def guess_year(date: datetime) -> datetime:
    now = datetime.now()
    try:
        current_year_date = date.replace(year=now.year)
    except ValueError:
        current_year_date = date
    try:
        last_year_date = date.replace(year=now.year-1)
    except ValueError:
        last_year_date = date
    return current_year_date if abs(current_year_date - now) < abs(last_year_date - now) else last_year_date

def parse_date(date_str: str) -> datetime:
    if len(date_str) == 4:
        return guess_year(datetime.strptime(date_str, "%m%d"))
    elif len(date_str) == 8:
        return datetime.strptime(date_str, "%Y%m%d")
    else:
        raise ValueError(f"Invalid date format: {date_str}")

def parse_time(time_str: str, base_date: datetime, support_48_hours: bool) -> Optional[datetime]:
    if time_str == '-':
        return None
    hour = int(time_str[:2])
    minute = int(time_str[2:])
    if support_48_hours:
        if 24 <= hour < 48:
            hour -= 24
            base_date += timedelta(days=1)
        elif hour >= 48:
            logger.error(f"Hour value out of range: {hour}")
            raise ValueError("Hour value out of range. Must be less than 48 when SUPPORT_48_HOURS is enabled.")
    elif hour >= 24:
        logger.error(f"Hour value out of range: {hour}")
        raise ValueError("Hour value out of range. Must be less than 24 when SUPPORT_48_HOURS is disabled.")
    return base_date.replace(hour=hour, minute=minute)

def convert_to_main_currency(amount: float, currency: str, currencies: Dict[str, Union[str, Tuple[str, float]]], main_currency: str) -> float:
    if currency == main_currency:
        return amount
    _, rate = currencies[currency]
    return amount * rate

def parse_xplit(file: Union[Path, str], **kwargs) -> XplitLog:
    logger.debug("Parsing xplit file")

    ALWAYS_INVOLVE_EVERYONE = kwargs.get('ALWAYS_INVOLVE_EVERYONE', False)
    SUPPORT_48_HOURS = kwargs.get('SUPPORT_48_HOURS', False)

    if isinstance(file, Path):
        file = file.read_text(encoding='utf-8')
    elif isinstance(file, str):
        with open(file, 'r', encoding='utf-8') as f:
            file = f.read()

    original_content = str(file)

    lines = file.splitlines()
    if not lines[0].startswith('@xplit'):
        logger.error("File does not start with @xplit")
        raise ValueError("File does not start with @xplit")
    
    version = lines[0].split()[1]
    if version != XPLIT_VERSION:
        logger.warning(f"Unmatched xplit record version: expected {XPLIT_VERSION}, got {version}")
    
    logger.debug(f"Version: {version}")

    lines = [uncomment_line(line) for line in lines if uncomment_line(line)]
    content = '\n'.join(lines)

    try:
        xplit_log_title = re.search(r'@title\s+(.*)', content).group(1)
        xplit_log_author = re.search(r'@author\s+(.*)', content).group(1)
        people_block = re.search(r'@people\n([\s\S]+?)\n@', content).group(1).strip()
        currencies_block = re.search(r'@currencies\n([\s\S]+?)\n@', content).group(1).strip()
        payment_methods_block = re.search(r'@payment_methods\n([\s\S]+?)\n@', content).group(1).strip()
        xplit_log_description = re.search(r'@description\n([\s\S]+?)\n@', content).group(1).strip()
        extra_payments_block = re.search(r'@extra_payments\n([\s\S]+?)\n@', content).group(1).strip()
    except AttributeError as e:
        logger.error(f"Failed to parse meta information: {e}")
        raise ValueError("Missing or malformed meta information")

    logger.debug(f"Title: {xplit_log_title}")
    logger.debug(f"Author: {xplit_log_author}")
    logger.debug(f"People block: {people_block}")
    logger.debug(f"Currencies block: {currencies_block}")
    logger.debug(f"Payment methods block: {payment_methods_block}")
    logger.debug(f"Description: {xplit_log_description}")
    logger.debug(f"Extra payments block: {extra_payments_block}")

    # Parsing people
    people = {line.split(':')[0].strip(): line.split(':')[1].strip() for line in people_block.split('\n')}
    logger.debug(f"People: {people}")

    # Parsing currencies
    currencies = {}
    currency_lines = currencies_block.split('\n')
    main_currency = currency_lines[0].split(':')[0].strip()
    currencies[main_currency] = currency_lines[0].split(':')[1].strip()
    for currency_line in currency_lines[1:]:
        parts = currency_line.split()
        symbol = parts[0].strip(':')
        name = parts[1].strip()
        rate = float(parts[3].strip())
        currencies[symbol] = (name, rate)
    logger.debug(f"Currencies: {currencies}")

    # Parsing payment methods
    payment_methods = {line.split(':')[0].strip(): line.split(':')[1].strip() for line in payment_methods_block.split('\n')}
    logger.debug(f"Payment Methods: {payment_methods}")

    # Parsing extra payments
    extra_payments = []
    for line in extra_payments_block.split('\n'):
        parts = line.split()
        payer_abbr = parts[0]
        receiver_abbr = parts[2].strip(':')
        amount = parts[3].strip()
        currency = amount[0]
        value = float(amount[1:])
        value_in_main_currency = convert_to_main_currency(value, currency, currencies, main_currency)
        payer = people.get(payer_abbr, payer_abbr)
        receiver = people.get(receiver_abbr, receiver_abbr)
        extra_payments.append((payer, receiver, value_in_main_currency))
    logger.debug(f"Extra Payments: {extra_payments}")

    # Entries
    entries = []
    current_section_title = None
    current_date = None
    entry_pattern = re.compile(r'"(.+?)"\s+"(.+?)"\s+([\d:-]+)\s+(\w+):(\w+)\s+(.+)')
    for idx, line in enumerate(lines):
        if line.startswith('@'):
            current_section_title = line[1:].strip()
            if re.match(r'\d{4}', current_section_title.split()[0]):
                current_date = parse_date(current_section_title.split()[0])
                if len(current_section_title.split(' ')) > 1:
                    current_section_title = "{date_str} {title}".format(date_str=current_date.strftime("%Y/%m/%d"), title=current_section_title.split(' ', maxsplit=1)[1])
                else:
                    current_section_title = current_date.strftime("%Y/%m/%d")
        else:
            match = entry_pattern.match(line)
            if match:
                title, description, time_str, paid_by, payment_method, details = match.groups()
                paid_by = people[paid_by]
                splits = {}
                total_expense = 0.0
                currency_match = re.search(r'([A-Z])(\d+(\.\d+)?)', details)
                if currency_match:
                    currency = currency_match.group(1)
                    total_expense = float(currency_match.group(2))
                    total_expense = convert_to_main_currency(total_expense, currency, currencies, main_currency)

                split_pattern = re.compile(r's\((\w+)\)([^s]+)')
                for split_match in split_pattern.finditer(details):
                    person_abbr, amount = split_match.groups()
                    try:
                        person = people[person_abbr]
                    except KeyError:
                        logger.error(f"Person abbreviation not found: {person_abbr}")
                        logger.debug(f"The error above occurred when parsing entry #{idx+1}: '{line}'")
                        raise ValueError(f"Person abbreviation not found: {person_abbr}")
                    if main_currency in amount:
                        split_amount = float(re.search(rf'{main_currency}(\d+(\.\d+)?)', amount).group(1))
                        splits[person] = split_amount
                    elif any(char.isdigit() for char in amount):  # Checking if it is a ratio or other currency
                        if main_currency in amount:
                            split_amount = float(re.search(rf'{main_currency}(\d+(\.\d+)?)', amount).group(1))
                        else:
                            currency_match = re.search(r'([A-Z])(\d+(\.\d+)?)', amount)
                            if currency_match:
                                currency = currency_match.group(1)
                                split_amount = float(currency_match.group(2))
                                split_amount = convert_to_main_currency(split_amount, currency, currencies, main_currency)
                            else:
                                split_amount = float(amount) * total_expense
                        splits[person] = split_amount
                    else:
                        splits[person] = False

                # If ALWAYS_INVOLVE_EVERYONE is enabled, calculate empty splits
                involved_people = list(splits.keys()) if not ALWAYS_INVOLVE_EVERYONE else list(people.values())
                for person in involved_people:
                    if person not in splits:
                        splits[person] = False

                # Calculating empty splits
                empty_splits = [person for person, amount in splits.items() if amount == False]
                if empty_splits:
                    allocated_amount = sum(amount for amount in splits.values() if amount > 1)
                    remaining_amount = total_expense - allocated_amount
                    split_value = remaining_amount / len(empty_splits)
                    for person in empty_splits:
                        splits[person] = split_value

                time = parse_time(time_str, current_date, SUPPORT_48_HOURS) if current_date else None
                entry = XplitEntry(current_section_title, title, description, time, paid_by, payment_methods[payment_method], total_expense, splits)
                entries.append(entry)

    return XplitLog(version, xplit_log_title, xplit_log_author, people, currencies, currencies[main_currency], payment_methods, xplit_log_description, entries, extra_payments, original_content)
