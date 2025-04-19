#!/usr/bin/env python3
from __future__ import annotations
import requests
import sys
import time


CONFIG_FILE_PATH = 'config'
RECORD_FILE_PATH = 'record'
MAX_NUM_RECORDS = 3


def log(message: str) -> None:
    print(message, file=sys.stderr)


class Activity:
    work_id: int
    work_title: str
    work_subtitle: str
    work_episode_id: int
    work_episode_number: str
    work_episode_title: str
    work_episode_rating_state: str
    work_episode_comment: str
    work_season: str
    work_url: str = ''
    status: str = ''
    action: str


def get_activities(user_id: int, access_token: str, num_fetch: int) -> list[Activity]:
    params = {
        'access_token': access_token,
        'filter_user_id': user_id,
        'per_page': num_fetch,
        'sort_id': 'desc',
        'fields': 'work.id,work.title,work.season_name_text,' \
                  'action,status.kind,' \
                  'record.comment,record.rating_state,' \
                  'episode.number_text,episode.title,episode.id',
    }
    resp = requests.get('https://api.annict.com/v1/activities', params)
    resp_json = resp.json()
    log(resp_json)
    resp.raise_for_status()

    result: list[Activity] = []

    for activity_info in resp_json['activities']:

        if activity_info['action'] == 'create_record':

            activity = Activity()
            work_info = activity_info['work']
            record_info = activity_info['record']
            episode_info = activity_info['episode']

            activity.work_id = work_info['id']
            activity.work_title = work_info['title']

            activity.work_episode_title = episode_info['title']
            activity.work_episode_number = episode_info['number_text']
            activity.work_episode_id = episode_info['id']

            activity.work_episode_comment = record_info['comment']
            activity.work_episode_rating_state = record_info['rating_state']

            activity.work_url = f'https://annict.com/works/{activity.work_id}/episodes/{activity.work_episode_id}'

            activity.action = activity_info['action']

            result.append(activity)

        elif activity_info['action'] == 'create_status':

            activity = Activity()
            work_info = activity_info['work']

            activity.work_id = work_info['id']
            activity.work_title = work_info['title']

            # put a space between number and kanji
            if 'season_name_text' in work_info:
                activity.work_season = f"{work_info['season_name_text'][:4]} {work_info['season_name_text'][4:]}"
            else:
                activity.work_season = "公開時期未定"

            activity.work_url = f'https://annict.com/works/{activity.work_id}'

            activity.status = activity_info['status']['kind']
            activity.action = activity_info['action']

            result.append(activity)

        else:
            continue
        
    return result[::-1]


def create_messages(activities: list[Activity]) -> list[str]:
    result: list[str] = []

    for activity in activities:

        if activity.action == 'create_status':
            if activity.status == 'watching':
                result.append(f'{activity.work_season}「{activity.work_title}」を観始めました。')
            elif activity.status == 'watched':
                result.append(f'{activity.work_season}「{activity.work_title}」を観終えました。')
            elif activity.status == 'wanna_watch':
                result.append(f'{activity.work_season}「{activity.work_title}」を観たいと思っています。')
            elif activity.status == 'on_hold':
                result.append(f'{activity.work_season}「{activity.work_title}」の視聴を一時停止しました。')
            elif activity.status == 'stop_watching':
                result.append(f'{activity.work_season}「{activity.work_title}」の視聴を中止しました。')
            else:
                result.append('')
                continue
        elif activity.action == 'create_record':
            result.append(f'「{activity.work_title}」{activity.work_episode_number} {activity.work_episode_title} を観ました。')
            # TODO: result.append(f'[{activity.work_episode_rating_state}]{activity.work_episode_comment}') などで感想コメントも出力する

        if activity.work_url != '':
            result[-1] += f'\n{activity.work_url}'

    return result


def is_already_posted(activity: Activity) -> bool:
    posted_activities: list[str]
    
    with open(RECORD_FILE_PATH, 'r') as record_file:
        posted_activities = record_file.read().split('\n')

    return f'{activity.work_id} {activity.status if activity.status else activity.work_episode_id}' in posted_activities


def update_record(activity: Activity) -> None:
    with open(RECORD_FILE_PATH, 'a') as record_file:
        print(activity.work_id, activity.status if activity.status else activity.work_episode_id, file=record_file)

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


def dry_run(messages: list[str], activities: list[Activity]) -> None:
    for message, activity in zip(messages, activities):
        if is_already_posted(activity) or message == '':
            continue

        print(message)
        update_record(activity)


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

    if len(sys.argv) == 1 or sys.argv[1] != 'dry':
        log('Posting to the Discord channel.')
        post_messages(
            int(config['DISCORD_CHANNEL_ID']),
            config['DISCORD_BOT_ACCESS_TOKEN'],
            messages,
            activities
        )
    else:
        dry_run(messages, activities)

    log('Done!')


if __name__ == '__main__':
    main()
