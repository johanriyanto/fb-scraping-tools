from collections import OrderedDict
from datetime import datetime
import copy
import dataset
import logging
import re


def append_times(new_times, times):
    """ Add times from new_times that are not in times.

    >>> append_times(OrderedDict([('1', {'times': [1500000000]})]), {})
    True
    >>> append_times(OrderedDict([('1', {'times': [1500000000]})]), \
{'1': {'times': [1500000000]}})
    False
    >>> append_times(OrderedDict([('2', {'times': [1500000000]})]), \
{'1': {'times': [1500000000]}})
    True
    >>> append_times(OrderedDict([('1', {'times': [1500000099]})]), \
{'1': {'times': [1500000000]}})
    True
    """
    changes = False
    for user in new_times.keys():

        new_lats = new_times[user]
        if "times" not in new_lats or not new_lats["times"]:
            logging.warn("No times found for user '{O}'".format(user))
            continue

        new_lats = new_times[user]["times"]

        if user not in times:
            times[user] = {"times": []}

        for new_lat in new_lats:
            if not times[user]["times"]:
                logging.info("User {0}: {1}".format(user, new_lat))
                times[user]["times"].append(new_lat)
                changes = True
            elif new_lat > times[user]["times"][-1]:
                logging.info("User {0}: {1} > {2}".format(
                    user, new_lat, times[user]["times"][-1]))
                times[user]["times"].append(new_lat)
                changes = True

    return changes


def process_data(times, user_infos,
                 set_optional_fields=False, denormalize=False):
    """ Parse names using user_infos and times.

    >>> process_data(OrderedDict([('mark.123', [1500])]), \
{'mark.123': {"id": 36, "Name": "John"}})
    [OrderedDict([('username', 'mark.123'), ('id', 36), ('name', 'John'), \
('times', ['1970-01-01 01:25:00'])])]

    >>> process_data(OrderedDict([('mark.123', [1500])]), \
{'mark.123': {"id": 36, "Year of birth": 1984}})
    [OrderedDict([('username', 'mark.123'), ('id', 36), \
('year_of_birth', 1984), ('times', ['1970-01-01 01:25:00'])])]

    >>> process_data(OrderedDict([('1', None)]), {'1': {"Name": "John"}})
    []

    >>> process_data(OrderedDict([('1', [])]), {'1': {"Name": "John"}})
    []

    >>> process_data(OrderedDict([('1', [1500])]), {})
    [OrderedDict([('id', 1), ('times', ['1970-01-01 01:25:00'])])]

    >>> process_data(OrderedDict([('1', [1500])]), {'1': {}})
    [OrderedDict([('id', 1), ('times', ['1970-01-01 01:25:00'])])]

    >>> process_data(OrderedDict([('1', [1500])]), {'1': {"Name": ""}})
    [OrderedDict([('id', 1), ('name', ''), \
('times', ['1970-01-01 01:25:00'])])]
    >>> process_data(OrderedDict([('mark.123', [1500, 1501])]), \
{'mark.123': {"id": 36, "Name": "John"}}, denormalize=True)
    [OrderedDict([('username', 'mark.123'), ('id', 36), ('name', 'John'), \
('time', '1970-01-01 01:25:00')]), OrderedDict([('username', 'mark.123'), \
('id', 36), ('name', 'John'), ('time', '1970-01-01 01:25:01')])]
    """

    parsed = []
    for user_id in times:

        parsed_user = OrderedDict()

        current_times = times[user_id]
        if not current_times:
            logging.warn(
                "Skipping user '{0}'".format(user_id))
            continue

        if user_id in user_infos and "id" in user_infos[user_id]:
            parsed_user["username"] = user_id
            parsed_user["id"] = user_infos[user_id]["id"]
        else:
            # Without user_infos, we need an id, not an username
            try:
                parsed_user["id"] = int(user_id)
            except Exception:
                logging.warn(
                    "Skipping user '{0}' with invalid id".format(user_id))
                continue

        tags = [
            'Name', 'Birthday', 'Education', 'Gender',
            'Relationship', 'Work', 'Year of birth']
        for tag in tags:
            escaped_tag = tag.replace(" ", "_").lower()
            if user_id in user_infos and tag in user_infos[user_id]:
                parsed_user[escaped_tag] = user_infos[user_id][tag]
            elif set_optional_fields:
                parsed_user[escaped_tag] = ""

        parsed_times = [
            str(datetime.fromtimestamp(int(time)))
            for time in current_times if int(time) != -1]

        if not denormalize:
            parsed_user["times"] = parsed_times
            parsed.append(parsed_user)
        else:
            for time in parsed_times:
                parsed_user["time"] = time
                parsed.append(copy.deepcopy(parsed_user))

    return parsed


def parse_date(date_str):
    """
    >>> parse_date("22 April 2011 at 20:34")
    datetime.datetime(2011, 4, 22, 20, 34)
    >>> parse_date("January 2017")
    datetime.datetime(2017, 1, 1, 0, 0)
    >>> parse_date("9 July 2011")
    datetime.datetime(2011, 7, 9, 0, 0)
    """

    try:
        return datetime.strptime(date_str, "%d %B %Y at %H:%M")

    except Exception:

        logging.info("Parsing date: {0} - date incomplete".format(date_str))

        # Date is not complete, e.g. missing day / year / time
        date_str_splitted = date_str.split(" at ")
        fill_date = "1 January 1900"
        fill_time = "00:00"

        if len(date_str_splitted) == 2:
            fill_date = date_str_splitted[0]
            fill_time = date_str_splitted[1]
        else:
            fill_date = date_str_splitted[0]

        day_found = re.match('^\d+.*', fill_date)
        if not day_found:
            logging.info("Parsing date: {0} - day not found".format(date_str))
            fill_date = "{0} {1}".format(1, fill_date)

        year_found = re.match('.*\d{4}.*', fill_date)
        if not year_found:
            logging.info(
                "Parsing date: {0}, year not found - "
                "assuming current year".format(date_str))
            fill_date = "{0} {1}".format(fill_date, datetime.now().year)

        try:
            parsed_date = datetime.strptime(fill_date, "%d %B %Y")
            parsed_time = datetime.strptime(fill_time, "%H:%M")
            parsed_date = datetime(
                parsed_date.year, parsed_date.month,
                parsed_date.day, parsed_time.hour,
                parsed_time.minute, parsed_time.second)

            return parsed_date

        except Exception:
            logging.error(
                "Parsing date: {0} - failed to deduce date".format(date_str))

    return datetime(1900, 1, 1, 0, 0)


def date_to_epoch(date):
    """
    >>> date_to_epoch(datetime(2011, 4, 22, 20, 34))
    1303497240
    """
    return (int)(date.strftime("%s"))


def save_to_db(data, database_path):

    if type(data) != list:
        logging.error("Invalid input - not a JSON list")
        return

    try:
        db = dataset.connect("sqlite:///{0}".format(database_path))

        times_table_name = "times"
        db.create_table(times_table_name, primary_id="_id")
        with db as tx:

            for user_data in data:

                if type(user_data) != OrderedDict:
                    logging.error(
                        "Invalid input - not a JSON list of dictionary")
                    return

                required_fields = [
                    'id', "time"
                ]
                for required_field in required_fields:
                    if required_field not in user_data:
                        logging.error("Invalid input - not found '{0}'".format(
                            required_field))
                        return

                tx[times_table_name].insert(user_data)

    except Exception as e:

        logging.error(
            "Failed to write to DB '{0}', "
            "got exception '{1}'".format(database_path, e))
