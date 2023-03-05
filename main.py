#!/usr/bin/env python3
from __future__ import annotations
import requests
import sys
import time


CONFIG_FILE_PATH = 'config'
RECORD_FILE_PATH = 'record'
MAX_NUM_RECORDS = 50


def log(message: str) -> None:
    print(message, file=sys.stderr)


class Activity:
    work_id: int
    work_title: str
    work_season: str
    work_url: str = ''
    status: str = ''


def get_activities(user_id: int, access_token: str, num_fetch: int) -> list[Activity]:
    params = {
        'access_token': access_token,
        'filter_user_id': user_id,
        'per_page': num_fetch,
        'sort_id': 'desc',
        'fields': 'action,work.id,work.title,work.official_site_url,' \
                  'work.wikipedia_url,work.season_name_text,status.kind',
    }
    resp = requests.get('https://api.annict.com/v1/activities', params)
    resp_json = resp.json()
    log(resp_json)
    resp.raise_for_status()

    result: list[Activity] = []

    for activity_info in resp_json['activities']:
        if activity_info['action'] != 'create_status':
            continue

        activity = Activity()
        work_info = activity_info['work']

        activity.work_id = work_info['id']
        activity.work_title = work_info['title']

        # put a space between number and kanji
        activity.work_season \
            = f"{work_info['season_name_text'][:4]} {work_info['season_name_text'][4:]}"

        # set url prioritizing the official one
        if work_info['official_site_url'] == '':
            activity.work_url = work_info['wikipedia_url']
        else:
            activity.work_url = work_info['official_site_url']

        # make sure to have '/' at the end of the URL
        if activity.work_url != '' and activity.work_url[-1] != '/':
            activity.work_url += '/'

        activity.status = activity_info['status']['kind']

        result.append(activity)

    return result[::-1]


def create_messages(activities: list[Activity]) -> list[str]:
    result: list[str] = []

    for activity in activities:
        if activity.status == 'watching':
            result.append(f'{activity.work_season}公開「{activity.work_title}」を観始めました。')
        elif activity.status == 'watched':
            result.append(f'{activity.work_season}公開「{activity.work_title}」を観終えました。')
        else:
            result.append('')
            continue

        if activity.work_url != '':
            result[-1] += f'\n{activity.work_url}'

    return result


def is_already_posted(activity: Activity) -> bool:
    posted_activities: list[str]
    
    with open(RECORD_FILE_PATH, 'r') as record_file:
        posted_activities = record_file.read().split('\n')

    return f'{activity.work_id} {activity.status}' in posted_activities


def update_record(activity: Activity) -> None:
    with open(RECORD_FILE_PATH, 'a') as record_file:
        print(activity.work_id, activity.status, file=record_file)

    recorded_activities: list[str]

    with open(RECORD_FILE_PATH, 'r') as record_file:
        recorded_activities = list(record_file.read().split('\n'))

    if len(recorded_activities) > MAX_NUM_RECORDS:
        with open(RECORD_FILE_PATH, 'w') as record_file:
            print(
                *recorded_activities[len(recorded_activities) - MAX_NUM_RECORDS:],
                sep='\n',
                file=record_file
            )


def post_messages(
    channel_id: int, access_token: str, messages: list[str], activities: list[Activity]) -> None:
    for message, activity in zip(messages, activities):
        if is_already_posted(activity) or message == '':
            continue

        headers = {
            'Authorization': f'Bot {access_token}',
            'Content-Type': 'application/json',
        }
        data = {
            'content': message
        }
        resp = requests.post(
            f'https://discordapp.com/api/channels/{channel_id}/messages',
            headers=headers,
            json=data
        )
        log(resp.json())
        resp.raise_for_status()

        update_record(activity)
        time.sleep(5)


def main() -> None:
    log('Reading the config file.')
    config: dict[str, str] = {}
    with open(CONFIG_FILE_PATH, 'r') as config_file:
        for line in config_file:
            key, value = line.split()
            config[key[:-1]] = value

    log('Fetching the activities from Annict.')
    activities = get_activities(
        int(config['ANNICT_USER_ID']),
        config['ANNICT_ACCESS_TOKEN'],
        int(config['ANNICT_NUM_FETCH_ONCE'])
    )
    messages = create_messages(activities)

    log('Posting to the discord channel.')
    post_messages(
        int(config['DISCORD_CHANNEL_ID']),
        config['DISCORD_BOT_ACCESS_TOKEN'],
        messages,
        activities
    )

    log('Done!')


if __name__ == '__main__':
    main()
