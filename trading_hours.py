#!/usr/bin/env python3
"""Build SPXW same-day trading-window ICS from a verified Cboe holiday snapshot."""
import argparse
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SOURCE = 'https://raw.githubusercontent.com/rickeylau/market-holidays/main/holidays.json'
OFFICIAL = 'https://www.cboe.com/about/hours/us-options/'
SPEC = 'https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications'
SNAPSHOT = ROOT / 'holidays_snapshot.json'
OUTPUT = ROOT / 'market-trading-hours.ics'
ET = ZoneInfo('America/New_York')


def validate(payload, current_year):
    if payload.get('source') != OFFICIAL:
        raise ValueError('Unexpected holiday source')
    stamp = payload['stamp']
    datetime.strptime(stamp, '%Y%m%dT%H%M%SZ')
    by_year = {}
    for item in payload['events']:
        day = date.fromisoformat(item['date'])
        close = item['close']
        if day.weekday() >= 5 or not item['holiday'] or close not in (None, '13:00'):
            raise ValueError(f'Unexpected holiday exception: {item}')
        year = by_year.setdefault(day.year, {})
        if day in year:
            raise ValueError(f'Duplicate holiday: {day}')
        year[day] = close
    if current_year not in by_year:
        raise ValueError(f'No verified schedule for current year {current_year}')
    for y, exceptions in by_year.items():
        if not 9 <= sum(v is None for v in exceptions.values()) <= 20 or len(exceptions) > 25:
            raise ValueError(f'Incomplete or unusual holiday schedule for {y}')
    return stamp, by_year


def sessions(by_year):
    for year, exceptions in sorted(by_year.items()):
        day = date(year, 1, 1)
        while day.year == year:
            close = exceptions.get(day, '16:00')
            if day.weekday() < 5 and close is not None:
                start = datetime.combine(day, time(9, 30), ET)
                end = datetime.combine(day, time.fromisoformat(close), ET)
                yield day, start, end, close == '13:00'
            day += timedelta(days=1)


def escape(value):
    return value.replace('\\', '\\\\').replace('\n', '\\n').replace(',', '\\,').replace(';', '\\;')


def fold(line):
    parts, part = [], ''
    for ch in line:
        if len((part + ch).encode('utf-8')) > 75:
            parts.append(part)
            part = ' ' + ch
        else:
            part += ch
    return '\r\n'.join(parts + [part])


def utc(dt):
    return dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def render(payload, current_year):
    stamp, by_year = validate(payload, current_year)
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Market Trading Hours//EN',
             'CALSCALE:GREGORIAN', 'X-WR-CALNAME:Market Trading Hours',
             'X-WR-TIMEZONE:America/New_York',
             'X-WR-CALDESC:SPXW same-day trading window; not extended hours or ES futures.']
    count = 0
    for day, start, end, early in sessions(by_year):
        count += 1
        title = 'US Trading Time (Early Close)' if early else 'US Trading Time'
        desc = (f'SPXW 0DTE strategy window: 09:30-{end:%H:%M} ET. '
                'Not the full SPX or ES trading session. Verify official notices before trading.\n'
                f'Cboe holidays: {OFFICIAL}\nSPXW specifications: {SPEC}')
        lines += ['BEGIN:VEVENT', f'UID:spxw-window-{day.isoformat()}@market-trading-hours',
                  f'DTSTAMP:{stamp}', f'DTSTART:{utc(start)}', f'DTEND:{utc(end)}',
                  f'SUMMARY:{escape(title)}', f'DESCRIPTION:{escape(desc)}',
                  'TRANSP:TRANSPARENT', f'URL:{SPEC}', 'END:VEVENT']
    lines.append('END:VCALENDAR')
    return ('\r\n'.join(fold(x) for x in lines) + '\r\n').encode('utf-8'), count, sorted(by_year)


def write_if_changed(path, data):
    if not path.exists() or path.read_bytes() != data:
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_bytes(data)
        tmp.replace(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--offline', action='store_true', help='Use local holiday snapshot')
    args = p.parse_args()
    current = datetime.now(ET).year
    old = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    if args.offline:
        payload = old
    else:
        request = Request(SOURCE, headers={'User-Agent': 'MarketTradingHours/1.0', 'Accept': 'application/json'})
        with urlopen(request, timeout=45) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError('Holiday snapshot too large')
        payload = json.loads(raw.decode('utf-8'))
        _, fresh = validate(payload, current)
        # Avoid removing dates from a previously published year if upstream loses coverage.
        prior_years = {date.fromisoformat(x['date']).year for x in old['events']}
        if not prior_years.issubset(fresh):
            raise ValueError(f'Previously covered years missing: {prior_years - set(fresh)}')
    data, count, years = render(payload, current)
    snapshot = (json.dumps(payload, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    write_if_changed(SNAPSHOT, snapshot)
    write_if_changed(OUTPUT, data)
    print(f'{count} sessions; verified years: {years}')
    if current + 1 not in years:
        print('::warning::Next-year holiday schedule not published yet; no sessions invented.')


if __name__ == '__main__':
    main()
