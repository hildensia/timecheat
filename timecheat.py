#!/usr/bin/env python
# encoding: utf-8

import argparse
from random import gauss
from math import sqrt, modf
from datetime import date, datetime, time, timedelta
import calendar
from printer import TextPrinter, LatexPrinter
import locale
from os import environ


week_workday_map = {
    'Monday': calendar.MONDAY,
    'Tuesday': calendar.TUESDAY,
    'Wednesday': calendar.WEDNESDAY,
    'Thursday': calendar.THURSDAY,
    'Friday': calendar.FRIDAY
}


def create_times(day, start, pausestart, worktime, pausetime, variance):
    mins_hours = modf(start)
    start = round_to_quarter(datetime.combine(day, time(int(mins_hours[1]),int(60*mins_hours[0]))) +
                             timedelta(hours=gauss(0, sqrt(variance))))
    pausetime = timedelta(hours=pausetime)
    worktime = timedelta(hours=worktime)
    pause_mins_hours = modf(pausestart)
    pausestart = round_to_quarter(datetime.combine(day, time(int(pause_mins_hours[1]),int(60*mins_hours[0]))) +
                                  timedelta(hours=gauss(0, sqrt(variance))))
    pauseend = pausestart + pausetime
    end = start + pausetime + worktime
    return (start, end, pausestart, pauseend)


def round_to_quarter(time):
    minutes_quarter = int(round((time.minute/60.)*4)/4*60)
    minutes_ten = int(round(time.minute/10.)*10)
    if abs(minutes_quarter-time.minute) < abs(minutes_ten-time.minute):
        minutes = minutes_quarter
    else:
        minutes = minutes_ten

    hours = time.hour
    if minutes == 60:
        minutes = 0
        hours += 1
    time = time.replace(hour=hours,minute=minutes)

    return time


def get_prev_year_month():
    today = date.today()
    # first day of the current month
    first = date(day=1, month=today.month, year=today.year)
    # the previous month
    previous = first - timedelta(days=1)
    return previous.year,  previous.month


def get_days_from_file(filenames):
    days = [datetime.strptime(line.strip(), '%d.%m.%Y').date()
            for f in filenames
            for line in open(f) if line.strip()]
    return days


def is_valid_week_workdays(week_workdays, possible_days):
    for day in week_workdays:
        if day not in possible_days:
            return False
    return True


def get_workdays_of_week(week_workdays):
    possible_days = week_workday_map.keys()
    if not week_workdays:
        week_workdays = possible_days
    if not is_valid_week_workdays(week_workdays, possible_days):
        return None

    return [week_workday_map[day] for day in week_workdays]


def get_work_days(year, month, holiday_files, unholiday_files, week_workdays):
    cal = calendar.Calendar()
    workdays = []
    holidays = get_days_from_file(holiday_files)
    unholidays = get_days_from_file(unholiday_files)
    for day in cal.itermonthdates(year, month):
        if (((day.weekday() in week_workdays and
                day not in holidays) or
                (day in unholidays)) and
                day.month == month):
            workdays.append(day)
    return workdays


def print_sheet(printer, workdays, args):
    printer.print_header(args.month)
    printer.print_divider()
    (_, week, _) = workdays[0].isocalendar()
    day_num_week = 0
    day_num_month = 0
    for day in workdays:
        (s, e, ps, pe) = create_times(day, args.start[0], args.pausestart[0],
                                      args.worktime[0], args.pausetime[0],
                                      args.variance[0])
        (_, weeknumber, _) = day.isocalendar()
        if weeknumber != week:
            printer.print_divider()
            printer.print_week(week, day_num_week, args.worktime[0])
            printer.print_divider()
            day_num_week = 0
            week = weeknumber
        day_num_week = day_num_week + 1
        day_num_month = day_num_month + 1
        printer.print_day(s, e, ps, pe, timedelta(hours=args.worktime[0]))
    if (day_num_week != 0):
        printer.print_divider()
        printer.print_week(week, day_num_week, args.worktime[0])
        printer.print_divider()
    printer.print_month(calendar.month_name[args.month], day_num_month,
                        args.worktime[0])
    printer.print_footer()


def main():
    try:
        locale.setlocale(locale.LC_TIME, environ['LOCALE'])
    except KeyError:  # no locale set
        pass

    prev_year, prev_month = get_prev_year_month()

    parser = argparse.ArgumentParser(description='Create a timesheet with ' +
                                     'gaussian distributed times for work.')
    parser.add_argument('--name', nargs='*', metavar='string',
                        type=str, help='Your name. Defaults to \'Max Mustermann\'.' +
                        'You can list as many names as you want (first middle last etc)'
                        'delimited by spaces.')
    parser.add_argument('--start', nargs=1, metavar='t_s', default=[8],
                        type=float, help='The time when work normally' +
                        ' starts. Default: 08:00 (=8).')
    parser.add_argument('--pausestart', nargs=1,  metavar='t_p',
                        default=[13], type=float, help='Time when the ' +
                        'lunch break normally starts. Default 13:00 (=13).')
    parser.add_argument('--worktime', nargs=1, metavar='t_d',  default=[8],
                        type=float, help='The duration of every work ' +
                        'day. Default: 8 hours (=8)')
    parser.add_argument('--pausetime', nargs=1, metavar='t_pt', default=[.5],
                        type=float, help='The duration of the lunch ' +
                        'break. Default: 30 min (=0.5)')
    parser.add_argument('--variance', nargs=1, metavar='var', default=[.25],
                        type=float, help='The variance of each start ' +
                        'time. Default: 15 min (=.25).')
    parser.add_argument('--year', metavar='year', default=prev_year, type=int,
                        help='The year for which the timesheet'
                        ' should be printed. Default: Current year')
    parser.add_argument('--month', metavar='month', default=prev_month,
                        type=int,
                        help='The month for which the timesheet'
                        ' should be printed. Default: previous month')
    parser.add_argument('--output', nargs=1, metavar='format',
                        default=['template'], type=str, help='The output format.' +
                        ' May be \'text\', \'template\'  or \'latex\'. ' +
                        'Default: template')
    parser.add_argument('--template', nargs=1, metavar='file',
                        default=['worksheet.tex'], type=str, help='If output' +
                        ' is \'template\' you can specify a template file.')
    parser.add_argument('--holidays', nargs='*', metavar='file',
                        default=['holidays'], type=str, help='A file ' +
                        'holiday dates. Format is each day in a line in ' +
                        ' german order, e.g.: 24.03.2013')
    parser.add_argument('--unholidays', nargs='*', metavar='file',
                        default=[], type=str,
                        help='A file ' +
                        'working dates. Format is each day in a line in ' +
                        ' german order, e.g.: 24.03.2013')
    parser.add_argument('--weekworkdays', nargs='*', metavar='string',
                        type=str, help='A list of workdays in the week. ' +
                        'Defaults to \'Monday Tuesday Wednesday Thursday Friday\','
                        'any subset of those days can be specified. The list ' +
                        'should be space delimited.')

    args = parser.parse_args()

    # Parse the week workdays (e.g. Monday, Tuesday, etc.).
    week_workdays = get_workdays_of_week(args.weekworkdays)
    if not week_workdays:
        print 'ERROR -- invalid week workdays:', args.weekworkdays
        exit(1)

    # Get the collection work days in this month based on the days of the week
    # you work.
    workdays = get_work_days(args.year, args.month, args.holidays,
                             args.unholidays, week_workdays)

    # If a name was specified in the args, then parse it out.
    name = ' '.join(args.name) if args.name else None

    # Figure out which printer to use.
    if args.output[0] == 'text':
        printer = TextPrinter()
    elif args.output[0] == 'template':
        printer = LatexPrinter(args.template[0], name=name)
    elif args.output[0] == 'latex':
        printer = LatexPrinter(name=name)
    else:
        parser.print_help()
        return
    print_sheet(printer, workdays, args)


if __name__ == "__main__":
    main()
