"""Shared form field parsers for the staff console."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time


def parse_decimal_field(raw_value, *, label, min_value=None):
    try:
        value = Decimal(str(raw_value).strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"{label} must be a valid number.")
    if min_value is not None and value < min_value:
        raise ValueError(f"{label} must be at least {min_value}.")
    return value


def parse_int_field(raw_value, *, label, min_value=None, max_value=None):
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError, AttributeError):
        raise ValueError(f"{label} must be a whole number.")
    if min_value is not None and value < min_value:
        raise ValueError(f"{label} must be at least {min_value}.")
    if max_value is not None and value > max_value:
        raise ValueError(f"{label} must be at most {max_value}.")
    return value


def parse_date_field(raw_value, *, label):
    raw = str(raw_value or "").strip()
    if not raw:
        raise ValueError(f"{label} must be a valid date.")
    value = parse_date(raw)
    if value is None:
        try:
            value = date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError(f"{label} must be a valid date.") from exc
    return value


def parse_datetime_field(raw_value, *, label):
    value = parse_datetime(str(raw_value or "").strip())
    if value is None:
        raise ValueError(f"{label} must be a valid date and time.")
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


def parse_optional_date_field(raw_value, *, label):
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    return parse_date_field(raw, label=label)


def parse_time_field(raw_value, *, label):
    value = parse_time(str(raw_value or "").strip())
    if value is None:
        raise ValueError(f"{label} must be a valid time.")
    return value


def csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


def guarding_redirect(target, *, anchor=""):
    url = reverse(target)
    return f"{url}#{anchor}" if anchor else url
