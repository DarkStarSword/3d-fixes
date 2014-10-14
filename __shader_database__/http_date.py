#!/usr/bin/env python3

import re

months = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
http_month_pattern = '(%s)' % '|'.join(months)
http_time_pattern = '\d\d:\d\d:\d\d'
http_date_pattern = re.compile(r'''^
    \S+
    (
        ,\s
        (?P<day1>\d+)
        (
            \s (?P<month1>{0}) \s (?P<year1>\d+)
        |
            - (?P<month2>{0}) - (?P<year2digit>\d+)
        )
        \s (?P<time1>{1}) \s GMT
    |
        \s (?P<month3>{0}) \s+ (?P<day2>\d+) \s (?P<time2>{1}) \s (?P<year3>\d+)
    )
$'''.format(http_month_pattern, http_time_pattern), re.VERBOSE)

def parse_http_date(date):
    '''
    Parses a string in any of the three standard HTTP-date formats (e.g. HTTP
    Last-Modified header) and returns it as seconds since UNIX EPOCH.

    It might be simpler to use time.strptime against the three possible
    formats and see which one works, but the locale specific stuff that does
    worries me since this string is locale agnostic. Maybe I'm just
    over-paranoid?
    '''
    import time
    import calendar
    match = http_date_pattern.match(date)
    if match is None:
        raise SyntaxError('Could not parse HTTP-date: %s' % date)
    match = match.groupdict()
    day = list(filter(None, (match['day1'], match['day2'])))
    assert(len(day) == 1)
    day = int(day[0])
    month = list(filter(None, (match['month1'], match['month2'], match['month3'])))
    assert(len(month) == 1)
    month = months.index(month[0]) + 1
    if match['year2digit']:
        year = int(match['year2digit'])
        cur_year = time.gmtime().tm_year
        if year > cur_year % 100 + 50:
            cur_year -= 50
        year += cur_year // 100 * 100
    else:
        year = list(filter(None, (match['year1'], match['year3'])))
        assert(len(year) == 1)
        year = int(year[0])
    t = list(filter(None, (match['time1'], match['time2'])))
    assert(len(t) == 1)
    (hour, min, sec) = map(int, t[0].split(':'))
    return calendar.timegm([year, month, day, hour, min, sec, 0, 0, 0])

